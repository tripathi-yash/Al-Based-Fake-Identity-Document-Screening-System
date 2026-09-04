"""
Generate DIY tampered document fixtures from clean MIDV-500 base images.

WHY THIS SCRIPT EXISTS:
MIDV-500 synthetic documents pass validation checks by design (they
correctly follow ICAO format standards) — they contain no forgeries.
Your four Module 3 signals (DL/ManTraNet, ELA, EXIF, copy-move) each
need fixtures that actually exercise their detection AND their known
blind spots, so thresholds can be calibrated against real numbers
instead of guesses, and the fusion logic can be demoed honestly.

WHERE THIS SITS:
    project_root/
      scripts/generate_tampered_fixtures.py   <- this file
      data/fixtures/clean/                    <- put MIDV-500 images here
      data/fixtures/tampered/                 <- output, auto-created

USAGE:
    python scripts/generate_tampered_fixtures.py

    Reads every image in data/fixtures/clean/, generates all 6 tamper
    categories per image (where applicable), writes outputs + a
    manifest.json describing exactly what was done to each fixture
    (so you can verify detector output against ground truth later).

CATEGORIES (mapped to which detector each one is meant to exercise):
  copy_move   -> copy_move.py            (SIFT+RANSAC should catch)
  splice      -> dl_tamper_detector.py   (DL should catch; copy-move
                                           CANNOT catch this by design —
                                           content comes from elsewhere)
  recompress  -> ela.py                  (should WEAKEN ela_score —
                                           proves ELA's honest limitation)
  exif_strip  -> exif_check.py           (should stay silent, not
                                           falsely read as "clean")
  exif_inject -> exif_check.py           (should flag editing_software)
  combined    -> tests fusion logic      (splice + recompress-after —
                                           the "attacker flattens after
                                           editing" case that proves why
                                           DL must be primary, not ELA)

Region selection for copy_move/splice is semi-automatic: by default it
picks a plausible-looking region (roughly where a photo/MRZ/field would
sit) using simple heuristics, but you can pass explicit boxes via
REGION_OVERRIDES below for specific known documents if the auto-pick
looks unrealistic. Review generated images visually before trusting them
as fixtures — that visual sanity check is the only "manual" step left.
"""
import io
import os
import json
import random
from pathlib import Path
from PIL import Image
import piexif  # instal this lib

random.seed(42)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CLEAN_DIR = PROJECT_ROOT / "data" / "fixtures" / "clean"
OUT_DIR = PROJECT_ROOT / "data" / "fixtures" / "tampered"

# Optional: {filename: (left, top, right, bottom)} to override auto region
# picking for specific images where the heuristic looks unrealistic.
REGION_OVERRIDES = {}


def _load_clean_images():
    exts = {".jpg", ".jpeg", ".png"}
    return sorted(p for p in CLEAN_DIR.iterdir() if p.suffix.lower() in exts)


def _auto_region(img: Image.Image, filename: str, frac=0.22):
    """Pick a plausible region size (~22% of shorter side) at a random
    but bounded position, unless an override is given for this file."""
    if filename in REGION_OVERRIDES:
        return REGION_OVERRIDES[filename]
    w, h = img.size
    side = int(min(w, h) * frac)
    max_x = max(w - side, 1)
    max_y = max(h - side, 1)
    x = random.randint(0, max_x)
    y = random.randint(0, max_y)
    return (x, y, x + side, y + side)


def gen_copy_move(img: Image.Image, filename: str) -> Image.Image:
    """Copy a region and paste it elsewhere in the SAME image —
    exercises copy_move.py's RANSAC-consistent-transform detection."""
    out = img.copy()
    w, h = out.size
    box = _auto_region(out, filename)
    patch = out.crop(box)
    side = box[2] - box[0]
    # paste far enough away to be a genuine duplication, not adjacent noise
    dest_x = min(max(w - side - 1, 0), (box[0] + w // 2) % max(w - side, 1))
    dest_y = min(max(h - side - 1, 0), (box[1] + h // 2) % max(h - side, 1))
    out.paste(patch, (dest_x, dest_y))
    return out


def gen_splice(img: Image.Image, donor: Image.Image, filename: str) -> Image.Image:
    """Paste a region from a DIFFERENT image — copy_move.py cannot catch
    this by design; this is what the DL detector exists for."""
    out = img.copy()
    box = _auto_region(out, filename)
    side_w, side_h = box[2] - box[0], box[3] - box[1]
    donor_resized = donor.resize((side_w, side_h))
    out.paste(donor_resized, (box[0], box[1]))
    return out


def gen_recompress(img: Image.Image, quality: int = 40, passes: int = 2) -> Image.Image:
    """Re-save at low quality multiple times — should WEAKEN the ELA
    signal, per ela.py's documented limitation. Not meant to be 'caught'
    cleanly; it's a fixture proving the system doesn't overclaim."""
    out = img.copy()
    for _ in range(passes):
        buf = io.BytesIO()
        out.save(buf, "JPEG", quality=quality)
        buf.seek(0)
        out = Image.open(buf).convert("RGB")
    return out


def gen_exif_strip(img: Image.Image) -> Image.Image:
    """Remove all EXIF — simulates WhatsApp/screenshot re-save.
    exif_check.py should stay silent (exif_present=False), not read
    this as evidence of a clean document."""
    data = list(img.getdata())
    out = Image.new(img.mode, img.size)
    out.putdata(data)
    return out


def gen_exif_inject(img: Image.Image, software: str = "Adobe Photoshop 25.0") -> bytes:
    """Inject an editing-software EXIF tag — exif_check.py should flag
    editing_software_detected. Returns raw bytes since piexif writes at
    the byte level, not via PIL Image object."""
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=95)
    buf.seek(0)
    jpeg_bytes = buf.read()

    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    exif_dict["0th"][piexif.ImageIFD.Software] = software
    exif_bytes = piexif.dump(exif_dict)

    out_buf = io.BytesIO()
    piexif.insert(exif_bytes, jpeg_bytes, out_buf)
    return out_buf.getvalue()


def gen_combined(img: Image.Image, donor: Image.Image, filename: str) -> Image.Image:
    """Splice + recompress afterward — the 'attacker flattens after
    editing' case. ELA alone would likely miss this; this fixture is
    what justifies DL-primary fusion in tampering_detection.py."""
    spliced = gen_splice(img, donor, filename)
    return gen_recompress(spliced, quality=45, passes=1)


def main():
    if not CLEAN_DIR.exists() or not any(CLEAN_DIR.iterdir()):
        raise FileNotFoundError(
            f"No clean base images found in {CLEAN_DIR}. "
            "Put MIDV-500 sample images there first."
        )

    clean_paths = _load_clean_images()
    manifest = []

    categories = ["copy_move", "splice", "recompress", "exif_strip", "exif_inject", "combined"]
    for cat in categories:
        (OUT_DIR / cat).mkdir(parents=True, exist_ok=True)

    for i, path in enumerate(clean_paths):
        img = Image.open(path).convert("RGB")
        filename = path.name
        # donor = a different clean image, for splice/combined
        donor_path = clean_paths[(i + 1) % len(clean_paths)]
        donor_img = Image.open(donor_path).convert("RGB")

        # 1. copy_move
        out = gen_copy_move(img, filename)
        out_path = OUT_DIR / "copy_move" / filename
        out.save(out_path, quality=95)
        manifest.append({"file": str(out_path.relative_to(PROJECT_ROOT)),
                          "category": "copy_move", "source": filename,
                          "expected_detector": "copy_move.py",
                          "ground_truth": "tampered"})

        # 2. splice (skip if only one clean image available)
        if len(clean_paths) > 1:
            out = gen_splice(img, donor_img, filename)
            out_path = OUT_DIR / "splice" / filename
            out.save(out_path, quality=95)
            manifest.append({"file": str(out_path.relative_to(PROJECT_ROOT)),
                              "category": "splice", "source": filename,
                              "donor": donor_path.name,
                              "expected_detector": "dl_tamper_detector.py",
                              "ground_truth": "tampered"})

        # 3. recompress
        out = gen_recompress(img)
        out_path = OUT_DIR / "recompress" / filename
        out.save(out_path, quality=95)
        manifest.append({"file": str(out_path.relative_to(PROJECT_ROOT)),
                          "category": "recompress", "source": filename,
                          "expected_detector": "ela.py (should show WEAKENED score)",
                          "ground_truth": "clean_but_recompressed"})

        # 4. exif_strip
        out = gen_exif_strip(img)
        out_path = OUT_DIR / "exif_strip" / filename
        out.save(out_path, quality=95)
        manifest.append({"file": str(out_path.relative_to(PROJECT_ROOT)),
                          "category": "exif_strip", "source": filename,
                          "expected_detector": "exif_check.py (should stay SILENT)",
                          "ground_truth": "clean_no_exif"})

        # 5. exif_inject
        jpeg_bytes = gen_exif_inject(img)
        out_path = OUT_DIR / "exif_inject" / filename
        out_path.write_bytes(jpeg_bytes)
        manifest.append({"file": str(out_path.relative_to(PROJECT_ROOT)),
                          "category": "exif_inject", "source": filename,
                          "expected_detector": "exif_check.py",
                          "ground_truth": "tampered"})

        # 6. combined
        if len(clean_paths) > 1:
            out = gen_combined(img, donor_img, filename)
            out_path = OUT_DIR / "combined" / filename
            out.save(out_path, quality=95)
            manifest.append({"file": str(out_path.relative_to(PROJECT_ROOT)),
                              "category": "combined", "source": filename,
                              "donor": donor_path.name,
                              "expected_detector": "fusion logic in tampering_detection.py",
                              "ground_truth": "tampered"})

    manifest_path = OUT_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"Generated {len(manifest)} fixtures from {len(clean_paths)} base images.")
    print(f"Manifest: {manifest_path}")
    print("Next: visually spot-check a few outputs, then run each Module 3 "
          "signal against these to calibrate thresholds_config.json.")


if __name__ == "__main__":
    main()