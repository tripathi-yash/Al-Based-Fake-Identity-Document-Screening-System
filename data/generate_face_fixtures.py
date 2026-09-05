"""
Generates FACE MATCH / MISMATCH fixtures for Module 4 testing.

WHAT THIS DOES:
For each teammate's selfie in data/raw_selfies/, creates a synthetic
"document" (reusing the same passport template style as generate_fixtures.py)
with that person's ACTUAL selfie pasted into the photo box -- instead of the
plain "PHOTO" placeholder text used in the identity fixtures.

Then builds two kinds of test pairs:
  - MATCHED pairs: person X's document + person X's own selfie
  - MISMATCHED pairs: person X's document + a DIFFERENT person's selfie

OUTPUT:
  data/fixtures/faces/matched/<name>_document.jpg
  data/fixtures/faces/matched/<name>_selfie.jpg
  data/fixtures/faces/mismatched/<docname>_vs_<selfiename>_document.jpg
  data/fixtures/faces/mismatched/<docname>_vs_<selfiename>_selfie.jpg
  data/fixtures/faces/face_pairs_manifest.json   <- lists every pair + expected result

WHY A SEPARATE JSON MANIFEST (not the main fixtures_manifest.csv):
Face testing needs TWO files per test case (a document + a selfie), but
fixtures_manifest.csv is built around ONE file per row. Rather than force
a bad fit, this small dedicated JSON cleanly lists every pair and its
expected outcome -- Module 4's tests read this directly.
"""

from PIL import Image, ImageDraw, ImageFont
import json
import os

RAW_SELFIES_DIR = "data/raw_selfies"
OUTPUT_DIR = "data/fixtures/faces"

# Map: person name -> their raw selfie filename (as actually saved on disk)
PEOPLE = {
    "anoop": "anoop.jpg",
    "ashray": "ashray.jpg",
    "riya": "riya.jpg",
    "srashti": "srashti.jpg",
    "yash": "yash.jpg",
}

# Passport-like numbers just for these face-fixture documents (F-prefixed to
# keep them clearly distinct from the N-prefixed identity fixtures already
# in fixtures_manifest.csv / Mock DB #1 -- avoids any ID collision/confusion)
PASSPORT_NUMBERS = {
    "anoop": "F1000001",
    "ashray": "F1000002",
    "riya": "F1000003",
    "srashti": "F1000004",
    "yash": "F1000005",
}


def load_font(candidates, size):
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def build_document_with_real_photo(person_name, selfie_path):
    """Same template style as generate_fixtures.py, but pastes the real
    selfie into the photo box instead of a placeholder."""
    W, H = 1000, 650
    img = Image.new("RGB", (W, H), color=(235, 235, 225))
    draw = ImageDraw.Draw(img)

    font_regular = load_font(["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"], 22)
    font_bold = load_font(["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"], 28)

    draw.text((30, 20), "REPUBLIC OF INDIA / PASSPORT", font=font_bold, fill=(20, 20, 80))
    draw.rectangle([(20, 10), (W - 20, H - 10)], outline=(20, 20, 80), width=3)

    photo_box_size = (200, 230)
    selfie = Image.open(selfie_path).convert("RGB")
    selfie = selfie.resize(photo_box_size)
    img.paste(selfie, (40, 90))
    draw.rectangle([(40, 90), (240, 320)], outline=(0, 0, 0), width=2)

    fields = [
        ("Surname", person_name.upper()),
        ("Given Name(s)", person_name.upper()),
        ("Passport No.", PASSPORT_NUMBERS[person_name]),
        ("Nationality", "INDIAN"),
    ]
    y = 90
    for label, value in fields:
        draw.text((270, y), f"{label}:", font=font_regular, fill=(0, 0, 0))
        draw.text((520, y), value, font=font_regular, fill=(0, 0, 50))
        y += 40

    return img


if __name__ == "__main__":
    matched_dir = os.path.join(OUTPUT_DIR, "matched")
    mismatched_dir = os.path.join(OUTPUT_DIR, "mismatched")
    os.makedirs(matched_dir, exist_ok=True)
    os.makedirs(mismatched_dir, exist_ok=True)

    names = list(PEOPLE.keys())
    pairs_manifest = []

    for name in names:
        selfie_path = os.path.join(RAW_SELFIES_DIR, PEOPLE[name])
        doc_img = build_document_with_real_photo(name, selfie_path)

        doc_out = os.path.join(matched_dir, f"{name}_document.jpg")
        selfie_out = os.path.join(matched_dir, f"{name}_selfie.jpg")

        doc_img.save(doc_out, quality=90)
        Image.open(selfie_path).convert("RGB").save(selfie_out, quality=90)

        pairs_manifest.append({
            "category": "matched",
            "document_file": f"matched/{name}_document.jpg",
            "selfie_file": f"matched/{name}_selfie.jpg",
            "document_identity": name,
            "selfie_identity": name,
            "expected_status": "match"
        })
        print(f"Created matched pair: {name}")

    for i, doc_name in enumerate(names):
        selfie_name = names[(i + 1) % len(names)]

        doc_selfie_path = os.path.join(RAW_SELFIES_DIR, PEOPLE[doc_name])
        doc_img = build_document_with_real_photo(doc_name, doc_selfie_path)

        wrong_selfie_path = os.path.join(RAW_SELFIES_DIR, PEOPLE[selfie_name])

        pair_id = f"{doc_name}_vs_{selfie_name}"
        doc_out = os.path.join(mismatched_dir, f"{pair_id}_document.jpg")
        selfie_out = os.path.join(mismatched_dir, f"{pair_id}_selfie.jpg")

        doc_img.save(doc_out, quality=90)
        Image.open(wrong_selfie_path).convert("RGB").save(selfie_out, quality=90)

        pairs_manifest.append({
            "category": "mismatched",
            "document_file": f"mismatched/{pair_id}_document.jpg",
            "selfie_file": f"mismatched/{pair_id}_selfie.jpg",
            "document_identity": doc_name,
            "selfie_identity": selfie_name,
            "expected_status": "mismatch"
        })
        print(f"Created mismatched pair: {doc_name}'s document vs {selfie_name}'s selfie")

    manifest_path = os.path.join(OUTPUT_DIR, "face_pairs_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(pairs_manifest, f, indent=2)

    print(f"\nDone. {len(pairs_manifest)} face pairs created.")
    print(f"Manifest written to: {manifest_path}")