"""
Generates Mock DB #2 supporting data and the "flawless forgery" demo fixture
for Module 5 (Authority Reference Match) testing.

PART 1: Establishes each face-fixture person's own selfie as their
"authority reference photo" - the independent, trusted record of what
they actually look like (see backend/database/mock_db2_authority_ref.py
for the actual lookup table).

PART 2: Builds the "flawless forgery" demo scenario described in
action_plan.pdf Section 4/6 - a document with a correctly-formatted,
unflagged ID number, but whose photo has been swapped to a different
person's face. Module 4 alone is fooled (the forger IS the person in the
photo); only Module 5 catches it (photo doesn't match the CLAIMED
identity's authority-registered reference).

OUTPUT:
  data/fixtures/faces/flawless_forgery/forged_document.jpg
  data/fixtures/faces/flawless_forgery/live_selfie_presented.jpg
  data/fixtures/faces/flawless_forgery/scenario.json
"""

from PIL import Image, ImageDraw, ImageFont
import json
import os

FACES_DIR = "data/fixtures/faces"

CLAIMED_IDENTITY = "anoop"
CLAIMED_PASSPORT_NUMBER = "F1000001"
FORGER_IDENTITY = "ashray"


def load_font(candidates, size):
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def build_forged_document():
    W, H = 1000, 650
    img = Image.new("RGB", (W, H), color=(235, 235, 225))
    draw = ImageDraw.Draw(img)
    font_regular = load_font(["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"], 22)
    font_bold = load_font(["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"], 28)

    draw.text((30, 20), "REPUBLIC OF INDIA / PASSPORT", font=font_bold, fill=(20, 20, 80))
    draw.rectangle([(20, 10), (W - 20, H - 10)], outline=(20, 20, 80), width=3)

    forger_selfie_path = os.path.join(FACES_DIR, "matched", f"{FORGER_IDENTITY}_selfie.jpg")
    forger_photo = Image.open(forger_selfie_path).convert("RGB").resize((200, 230))
    img.paste(forger_photo, (40, 90))
    draw.rectangle([(40, 90), (240, 320)], outline=(0, 0, 0), width=2)

    fields = [
        ("Surname", CLAIMED_IDENTITY.upper()),
        ("Given Name(s)", CLAIMED_IDENTITY.upper()),
        ("Passport No.", CLAIMED_PASSPORT_NUMBER),
        ("Nationality", "INDIAN"),
    ]
    y = 90
    for label, value in fields:
        draw.text((270, y), f"{label}:", font=font_regular, fill=(0, 0, 0))
        draw.text((520, y), value, font=font_regular, fill=(0, 0, 50))
        y += 40

    return img


if __name__ == "__main__":
    out_dir = os.path.join(FACES_DIR, "flawless_forgery")
    os.makedirs(out_dir, exist_ok=True)

    forged_doc = build_forged_document()
    forged_doc_path = os.path.join(out_dir, "forged_document.jpg")
    forged_doc.save(forged_doc_path, quality=90)

    forger_selfie_path = os.path.join(FACES_DIR, "matched", f"{FORGER_IDENTITY}_selfie.jpg")
    live_selfie_path = os.path.join(out_dir, "live_selfie_presented.jpg")
    Image.open(forger_selfie_path).convert("RGB").save(live_selfie_path, quality=90)

    scenario = {
        "scenario_name": "flawless_forgery_own_face_swap",
        "description": (
            f"Document claims identity {CLAIMED_IDENTITY.upper()} ({CLAIMED_PASSPORT_NUMBER}) "
            f"but the photo has been swapped to {FORGER_IDENTITY.upper()} (the forger). "
            "The forger presents his own live selfie at the checkpoint."
        ),
        "forged_document_file": "flawless_forgery/forged_document.jpg",
        "live_selfie_file": "flawless_forgery/live_selfie_presented.jpg",
        "claimed_identity": CLAIMED_IDENTITY,
        "claimed_passport_number": CLAIMED_PASSPORT_NUMBER,
        "actual_person_in_photo": FORGER_IDENTITY,
        "expected_module2_result": "checksum_pass=true, db_status=clear (document itself is not flagged - that's the whole point)",
        "expected_module4_result": "match (forger IS the person in the swapped photo - Module 4 alone is fooled)",
        "expected_module5_result": f"mismatch (document photo does not match the authority reference for {CLAIMED_PASSPORT_NUMBER}, which is {CLAIMED_IDENTITY.upper()}'s real face, not {FORGER_IDENTITY.upper()}'s)",
        "authority_reference_used": f"data/fixtures/faces/matched/{CLAIMED_IDENTITY}_selfie.jpg (via Mock DB 2, key {CLAIMED_PASSPORT_NUMBER})"
    }
    scenario_path = os.path.join(out_dir, "scenario.json")
    with open(scenario_path, "w") as f:
        json.dump(scenario, f, indent=2)

    print(f"Created: {forged_doc_path}")
    print(f"Created: {live_selfie_path}")
    print(f"Created: {scenario_path}")
    print("\nThis is your strongest demo moment - Module 4 passes this, Module 5 catches it.")