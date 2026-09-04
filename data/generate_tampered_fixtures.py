"""
Generates TAMPERED passport fixtures for Module 3 testing.

WHY THE "DOUBLE SAVE" MATTERS:
Real tampering-detection (ELA) works by finding compression inconsistencies
that appear when an already-compressed JPEG is edited and re-saved. If we
generated a "tampered" image in a single save (like our clean fixtures),
it would look just as clean as a real clean document -- defeating the
purpose. So every fixture here:
  1. Opens an EXISTING clean fixture JPEG (already saved once)
  2. Edits a specific region of it
  3. Saves it again as JPEG (this second save is what creates a genuine,
     detectable compression-inconsistency signature)

THREE TAMPER TYPES (matching action_plan.pdf Section 4, Module 3):
  1. photo_swap   - the "photo" region is overwritten (simulates photo replacement)
  2. dob_alter    - the printed DOB text is overwritten with a different date,
                    but the MRZ at the bottom is NOT touched/recomputed.
                    This deliberately creates a "text vs MRZ mismatch" --
                    Module 2's cross-check should catch this one, not Module 3.
  3. stamp_clone  - a region of the image is copy-pasted onto another region
                    (simulates copy-move/stamp-cloning forgery)

OUTPUT (per fixture):
  data/fixtures/tampered/tampered_XX_<type>.jpg
  data/fixtures/tampered/tampered_XX_<type>.json   <- what was changed + expected results
"""

from PIL import Image, ImageDraw, ImageFont
import json
import os

SOURCE_DIR = "data/fixtures/clean"
OUTPUT_DIR = "data/fixtures/tampered"

def load_font(candidates, size):
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def make_photo_swap(source_json, index):
    """Overwrite the photo placeholder region -- simulates a photo swap."""
    img_path = os.path.join(SOURCE_DIR, source_json["filename"])
    img = Image.open(img_path).convert("RGB")   # load already-saved JPEG
    draw = ImageDraw.Draw(img)

    draw.rectangle([(40, 90), (240, 320)], fill=(180, 150, 130))
    font = load_font(["arial.ttf", "DejaVuSans.ttf"], 18)
    draw.text((60, 190), "SWAPPED", font=font, fill=(80, 20, 20))

    out_name = f"tampered_{index:02d}_photo_swap.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    img.save(out_path, quality=90)  # SECOND save -> real compression inconsistency

    meta = {
        "filename": out_name,
        "doc_type": "passport",
        "tamper_type": "photo_swap",
        "based_on": source_json["filename"],
        "linked_db_id": source_json["fields"]["passport_number"],
        "what_was_changed": "Photo placeholder region overwritten with a different fill/text, image re-saved (double JPEG compression).",
        "expected_module3_result": True,
        "expected_module2_result": "checksum_pass=true (MRZ untouched)",
        "expected_module4_result": "no_face_detected (no real face in either version)"
    }
    with open(out_path.replace(".jpg", ".json"), "w") as f:
        json.dump(meta, f, indent=2)
    return out_name


def make_dob_alter(source_json, index):
    """Overwrite the printed DOB text only -- MRZ at bottom is left untouched.
    This creates a genuine text-vs-MRZ mismatch, which is Module 2's job to catch."""
    img_path = os.path.join(SOURCE_DIR, source_json["filename"])
    img = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    dob_row_y = 90 + 4 * 40
    draw.rectangle([(510, dob_row_y - 2), (750, dob_row_y + 28)], fill=(235, 235, 225))
    font = load_font(["arial.ttf", "DejaVuSans.ttf"], 22)

    altered_dob = "1990-01-01"
    draw.text((520, dob_row_y), altered_dob, font=font, fill=(0, 0, 50))

    out_name = f"tampered_{index:02d}_dob_alter.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    img.save(out_path, quality=90)

    meta = {
        "filename": out_name,
        "doc_type": "passport",
        "tamper_type": "dob_alter",
        "based_on": source_json["filename"],
        "linked_db_id": source_json["fields"]["passport_number"],
        "what_was_changed": f"Printed Date of Birth overwritten to '{altered_dob}'. MRZ line (still says {source_json['fields']['date_of_birth']}) was NOT updated -- deliberate text/MRZ mismatch.",
        "expected_module3_result": False,
        "expected_module2_result": "checksum_pass=true, text_mrz_match=false -- THIS is the catch",
        "expected_module4_result": "no_face_detected (no real face in either version)"
    }
    with open(out_path.replace(".jpg", ".json"), "w") as f:
        json.dump(meta, f, indent=2)
    return out_name


def make_stamp_clone(source_json, index):
    """Copy a region of the image and paste it elsewhere -- simulates copy-move/stamp forgery."""
    img_path = os.path.join(SOURCE_DIR, source_json["filename"])
    img = Image.open(img_path).convert("RGB")

    region_box = (270, 90, 850, 130)
    region = img.crop(region_box)
    paste_target = (270, 420)
    img.paste(region, paste_target)

    out_name = f"tampered_{index:02d}_stamp_clone.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_name)
    img.save(out_path, quality=90)

    meta = {
        "filename": out_name,
        "doc_type": "passport",
        "tamper_type": "stamp_clone",
        "based_on": source_json["filename"],
        "linked_db_id": source_json["fields"]["passport_number"],
        "what_was_changed": f"Region {region_box} duplicated and pasted at {paste_target} -- simulates copy-move/cloned stamp forgery.",
        "expected_module3_result": True,
        "expected_module2_result": "checksum_pass=true (MRZ untouched)",
        "expected_module4_result": "no_face_detected (no real face in either version)"
    }
    with open(out_path.replace(".jpg", ".json"), "w") as f:
        json.dump(meta, f, indent=2)
    return out_name


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(os.path.join(SOURCE_DIR, "clean_passport_01.json")) as f:
        base_meta = json.load(f)

    f1 = make_photo_swap(base_meta, 1)
    print(f"Created: {f1}")
    f2 = make_dob_alter(base_meta, 2)
    print(f"Created: {f2}")
    f3 = make_stamp_clone(base_meta, 3)
    print(f"Created: {f3}")

    print(f"\nDone. 3 tampered fixtures created in '{OUTPUT_DIR}/'")