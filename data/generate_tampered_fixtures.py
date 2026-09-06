"""
generate_tampered_fixtures.py — corrected fixture generator.

WHY THE OLD SCRIPT FAILED (confirmed by inspecting the actual rendered
fixtures you uploaded):
  - photo_swap: painted a solid rectangle + "SWAPPED" text into the photo
    box. No real face -> no forgery signal for ManTraNet/ELA to catch
    beyond a flat color block, and DeepFace can't even find a face for
    Module 4 either. Result: tamper_verdict stayed "clean".
  - stamp_clone: clean_passport_01.jpg has NO stamp/seal anywhere (it's
    plain text on a cream background). Copying an arbitrary text block
    ("Surname: SHARMA") gives SIFT almost no distinctive, textured
    keypoints (flat text on flat background) -> RANSAC never finds
    enough consistent inliers -> copy_move_flag stayed False.

FIX:
  - photo_swap: paste a REAL face photo (your teammate's selfie) into
    the actual photo box, resized to fit, then re-save as JPEG (forces
    double-compression -> ELA signal too).
  - stamp_clone: since no real stamp exists, first draw a synthetic but
    visually rich circular seal (concentric rings + text + a starburst)
    onto an empty part of the page -> this gives SIFT plenty of
    distinctive keypoints. Then copy that exact region to a second empty
    location, keeping the original in place (genuine copy-move).
  - dob_alter: unchanged in spirit — overwrite ONLY the printed DOB
    text, leave the MRZ untouched. (Your existing test for this already
    passes, so this is just kept for completeness / reproducibility.)

BEFORE RUNNING:
  1. Save your teammate's real selfie/portrait somewhere in the project,
     e.g.:
         data/fixtures/team/swap_source_face.jpg
     (any real, clearly-different-person face photo works — the point
     is DeepFace/ManTraNet see an actual face, not a color block.)
  2. Open clean_passport_01.jpg yourself in an image viewer and confirm
     PHOTO_BOX / STAMP_BOX_A / STAMP_BOX_B below don't overlap any real
     text. Coordinates here were estimated from the fixture screenshots
     you shared — adjust the four numbers if they're off by a bit on
     your actual file (dimensions matter more than perfection; SIFT/
     ManTraNet don't need pixel-perfect placement).
  3. Run:
         python generate_tampered_fixtures.py
  4. Then:
         pytest tests/test_module3_tampering.py -v
"""
import json
import os
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CLEAN_DIR = os.path.join(PROJECT_ROOT, "data", "fixtures", "clean")
TAMPERED_DIR = os.path.join(PROJECT_ROOT, "data", "fixtures", "tampered")
TEAM_DIR = os.path.join(PROJECT_ROOT, "data", "raw_selfies")

CLEAN_IMAGE_PATH = os.path.join(CLEAN_DIR, "clean_passport_01.jpg")
CLEAN_JSON_PATH = os.path.join(CLEAN_DIR, "clean_passport_01.json")

SWAP_FACE_SOURCE = os.path.join(TEAM_DIR, "yash.jpg")

LINKED_DB_ID = "N1234567"

# --- Coordinates estimated from the actual fixture layout (verify against
#     your real clean_passport_01.jpg and adjust if needed) ---
PHOTO_BOX = (40, 90, 240, 320)          # the existing photo placeholder box
STAMP_BOX_A = (660, 380, 900, 500)      # empty area, right side, below fields, above MRZ
STAMP_BOX_B = (40, 350, 280, 470)       # empty area, left side, below photo box
DOB_LABEL_ROW_Y = (250, 275)            # approx y-range of the "Date of Birth:" printed row
DOB_VALUE_X = (520, 700)                # approx x-range of the printed DOB value


def _load_clean():
    if not os.path.isfile(CLEAN_IMAGE_PATH):
        raise FileNotFoundError(f"Clean fixture not found: {CLEAN_IMAGE_PATH}")
    return Image.open(CLEAN_IMAGE_PATH).convert("RGB")


def _load_clean_meta():
    if os.path.isfile(CLEAN_JSON_PATH):
        with open(CLEAN_JSON_PATH) as f:
            return json.load(f)
    return {}


def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# 1. photo_swap — real face replacement
# ---------------------------------------------------------------------------
def make_photo_swap():
    if not os.path.isfile(SWAP_FACE_SOURCE):
        raise FileNotFoundError(
            f"Put a real face photo (different person) at: {SWAP_FACE_SOURCE}\n"
            "e.g. save the teammate selfie there before running this script."
        )

    base = _load_clean()
    face = Image.open(SWAP_FACE_SOURCE).convert("RGB")

    x1, y1, x2, y2 = PHOTO_BOX
    box_w, box_h = x2 - x1, y2 - y1

    # Center-crop the face photo to the box's aspect ratio, then resize —
    # avoids a squashed/distorted face that could hurt face detection.
    fw, fh = face.size
    box_aspect = box_w / box_h
    face_aspect = fw / fh
    if face_aspect > box_aspect:
        new_w = int(fh * box_aspect)
        left = (fw - new_w) // 2
        face = face.crop((left, 0, left + new_w, fh))
    else:
        new_h = int(fw / box_aspect)
        top = (fh - new_h) // 2
        face = face.crop((0, top, fw, top + new_h))
    face = face.resize((box_w, box_h), Image.LANCZOS)

    tampered = base.copy()
    tampered.paste(face, (x1, y1))

    out_path = os.path.join(TAMPERED_DIR, "tampered_01_photo_swap.jpg")
    # quality=85 (vs a typical clean-fixture save at ~95) -> real double
    # JPEG compression difference for ELA to pick up, not just pixel edit.
    tampered.save(out_path, "JPEG", quality=85)

    meta = {
        "filename": "tampered_01_photo_swap.jpg",
        "doc_type": "passport",
        "tamper_type": "photo_swap",
        "based_on": "clean_passport_01.jpg",
        "linked_db_id": LINKED_DB_ID,
        "what_was_changed": (
            f"Portrait region {PHOTO_BOX} replaced with a real, different "
            f"person's face photo ({os.path.basename(SWAP_FACE_SOURCE)}), "
            "resized/center-cropped to fit, then re-saved at JPEG quality=85 "
            "(double compression vs. the clean original)."
        ),
        "source_region": None,
        "target_region": list(PHOTO_BOX),
        "expected_module3_result": True,
        "expected_module2_result": "checksum_pass=true (MRZ untouched)",
        "expected_module4_result": "mismatch (document photo is now a different real face than the live selfie)",
        "expected_module5_result": "mismatch (swapped photo no longer matches mock_db2's authority-original photo for this passport number)",
    }
    _save_json(os.path.join(TAMPERED_DIR, "tampered_01_photo_swap.json"), meta)
    print(f"[photo_swap] wrote {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# 2. stamp_clone — synthesize a real stamp, then copy-move it
# ---------------------------------------------------------------------------
def _draw_synthetic_stamp(draw: ImageDraw.ImageDraw, box):
    """Draws a visually rich circular seal into `box` — concentric rings,
    radial ticks, and text — specifically to give SIFT plenty of
    distinctive, high-contrast keypoints (a requirement copy-move
    detection needs; flat text/backgrounds don't provide this)."""
    x1, y1, x2, y2 = box
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    r_outer = min(x2 - x1, y2 - y1) // 2 - 4

    seal_color = (140, 20, 30)  # official-looking dark red

    for r in (r_outer, r_outer - 6, r_outer - 22):
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=seal_color, width=3)

    # Radial ticks around the middle ring for extra distinctive texture
    import math
    for angle_deg in range(0, 360, 15):
        angle = math.radians(angle_deg)
        r_in, r_out = r_outer - 14, r_outer - 6
        x_in, y_in = cx + r_in * math.cos(angle), cy + r_in * math.sin(angle)
        x_out, y_out = cx + r_out * math.cos(angle), cy + r_out * math.sin(angle)
        draw.line((x_in, y_in, x_out, y_out), fill=seal_color, width=2)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 14)
    except Exception:
        font = ImageFont.load_default()

    draw.text((cx, cy - 8), "OFFICIAL", fill=seal_color, font=font, anchor="mm")
    draw.text((cx, cy + 10), "SEAL", fill=seal_color, font=font, anchor="mm")


def make_stamp_clone():
    base = _load_clean()

    # Step 1: since the clean fixture has NO real stamp, synthesize one
    # first (per doc-36 instructions) — this becomes the "genuine" stamp
    # in both the source-of-truth and the tampered copy.
    stamped_base = base.copy()
    draw = ImageDraw.Draw(stamped_base)
    _draw_synthetic_stamp(draw, STAMP_BOX_A)

    # Step 2: genuine copy-move — crop the exact stamp region and paste
    # it, unmodified, at a second empty location. Original stays in place.
    region = stamped_base.crop(STAMP_BOX_A)
    tw, th = STAMP_BOX_B[2] - STAMP_BOX_B[0], STAMP_BOX_B[3] - STAMP_BOX_B[1]
    region = region.resize((tw, th), Image.LANCZOS)

    tampered = stamped_base.copy()
    tampered.paste(region, (STAMP_BOX_B[0], STAMP_BOX_B[1]))

    out_path = os.path.join(TAMPERED_DIR, "tampered_03_stamp_clone.jpg")
    tampered.save(out_path, "JPEG", quality=92)

    meta = {
        "filename": "tampered_03_stamp_clone.jpg",
        "doc_type": "passport",
        "tamper_type": "stamp_clone",
        "based_on": "clean_passport_01.jpg",
        "linked_db_id": LINKED_DB_ID,
        "what_was_changed": (
            "clean_passport_01.jpg contains no real stamp/seal, so a "
            f"synthetic official seal was first drawn at {STAMP_BOX_A}. "
            f"That exact region was then cropped and duplicated at "
            f"{STAMP_BOX_B} (resized to fit), simulating a copy-move "
            "forgery of an official seal. The original seal remains in "
            "place at its original location — this is NOT a "
            "replace-and-delete edit."
        ),
        "source_region": list(STAMP_BOX_A),
        "target_region": list(STAMP_BOX_B),
        "expected_module3_result": True,
        "expected_module2_result": "checksum_pass=true (MRZ untouched)",
        "expected_module4_result": "no_face_detected (no real face in either version)",
    }
    _save_json(os.path.join(TAMPERED_DIR, "tampered_03_stamp_clone.json"), meta)
    print(f"[stamp_clone] wrote {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# 3. dob_alter — visible-text-only edit, MRZ untouched (kept for completeness)
# ---------------------------------------------------------------------------
def make_dob_alter():
    base = _load_clean()
    tampered = base.copy()
    draw = ImageDraw.Draw(tampered)

    x1, x2 = DOB_VALUE_X
    y1, y2 = DOB_LABEL_ROW_Y
    # Paint over the printed DOB value with the page background color,
    # then write a different date in the same style/position.
    bg_color = base.getpixel((x1 - 10, y1 + 5))
    draw.rectangle((x1, y1, x2, y2), fill=bg_color)

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 20)
    except Exception:
        font = ImageFont.load_default()

    ALTERED_DOB_TEXT = "1990-01-01"
    draw.text((x1, y1), ALTERED_DOB_TEXT, fill=(20, 20, 90), font=font)

    out_path = os.path.join(TAMPERED_DIR, "tampered_02_dob_alter.jpg")
    tampered.save(out_path, "JPEG", quality=95)

    meta = {
        "filename": "tampered_02_dob_alter.jpg",
        "doc_type": "passport",
        "tamper_type": "dob_alter",
        "based_on": "clean_passport_01.jpg",
        "linked_db_id": LINKED_DB_ID,
        "what_was_changed": (
            f"Printed DOB value region {DOB_VALUE_X + DOB_LABEL_ROW_Y} "
            f"overwritten with '{ALTERED_DOB_TEXT}'. MRZ line 2 (which "
            "still encodes the original 2003-08-15) was NOT modified — "
            "this is a text-vs-MRZ inconsistency, a Module 2 catch, not "
            "a Module 3 catch."
        ),
        "source_region": None,
        "target_region": [x1, y1, x2, y2],
        "expected_module3_result": False,
        "expected_module2_result": "text_mrz_mismatch_dob in flags; checksum_pass=true",
    }
    _save_json(os.path.join(TAMPERED_DIR, "tampered_02_dob_alter.json"), meta)
    print(f"[dob_alter] wrote {out_path}")
    return out_path


if __name__ == "__main__":
    os.makedirs(TAMPERED_DIR, exist_ok=True)
    print("Clean fixture metadata (for cross-reference):", _load_clean_meta())
    make_photo_swap()
    make_dob_alter()
    make_stamp_clone()
    print("\nDone. Now run: pytest tests/test_module3_tampering.py -v")