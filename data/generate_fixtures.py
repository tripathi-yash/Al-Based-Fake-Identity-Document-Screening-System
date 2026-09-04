"""
Generates CLEAN passport fixture images + matching ground-truth JSON files.

WHY THIS EXISTS:
The team's action plan originally called for using the MIDV-500 dataset for
base clean documents + ground truth. The downloadable Hugging Face copy of
MIDV-500 we had access to did not retain the original field-level ground
truth (its "label" column turned out to be another image, not text data).
To avoid fabricating claims about data that doesn't exist, we generate our
own synthetic, ICAO 9303-compliant passport fixtures instead. Every field
value here is 100% known and correct because we generated it ourselves.

OUTPUT (per fixture):
  data/fixtures/clean/clean_passport_XX.jpg   <- the document image
  data/fixtures/clean/clean_passport_XX.json  <- ground-truth field values

Run this script once; it will create N_FIXTURES clean fixtures.
"""

from PIL import Image, ImageDraw, ImageFont
import json
import os

# ---------- CONFIG ----------
OUTPUT_DIR = "data/fixtures/clean"
N_FIXTURES = 5

# A small pool of varied sample identities (self-invented, clearly synthetic)
SAMPLE_PEOPLE = [
    {"surname": "SHARMA", "given_names": "ASHRAY KUMAR", "passport_no": "N1234567",
     "nationality": "IND", "dob": "030815", "sex": "M", "expiry": "300815"},
    {"surname": "VERMA", "given_names": "PRIYA", "passport_no": "N2345678",
     "nationality": "IND", "dob": "990112", "sex": "F", "expiry": "290312"},
    {"surname": "KHAN", "given_names": "AAMIR RAZA", "passport_no": "N3456789",
     "nationality": "IND", "dob": "011225", "sex": "M", "expiry": "311225"},
    {"surname": "IYER", "given_names": "LAKSHMI", "passport_no": "N4567890",
     "nationality": "IND", "dob": "970630", "sex": "F", "expiry": "280630"},
    {"surname": "SINGH", "given_names": "ARJUN", "passport_no": "N5678901",
     "nationality": "IND", "dob": "020914", "sex": "M", "expiry": "320914"},
]

# ---------- MRZ CHECKSUM LOGIC (ICAO 9303 standard) ----------
def char_value(c):
    if c == '<':
        return 0
    if c.isdigit():
        return int(c)
    return ord(c) - ord('A') + 10

def check_digit(data):
    weights = [7, 3, 1]
    total = 0
    for i, c in enumerate(data):
        total += char_value(c) * weights[i % 3]
    return str(total % 10)

def pad(s, length):
    return (s + '<' * length)[:length]

def yymmdd_to_iso(yymmdd, is_dob=True):
    """Convert MRZ's YYMMDD to ISO 8601 YYYY-MM-DD (schema requires ISO dates)."""
    yy, mm, dd = yymmdd[0:2], yymmdd[2:4], yymmdd[4:6]
    if is_dob:
        century = "19" if int(yy) > 30 else "20"
    else:
        century = "20"
    return f"{century}{yy}-{mm}-{dd}"

def build_passport_mrz(surname, given_names, passport_no, nationality,
                        dob_yymmdd, sex, expiry_yymmdd, country="IND"):
    name_field = f"{surname}<<{given_names}".replace(" ", "<")
    line1 = pad(f"P<{country}{name_field}", 44)

    passport_no_p = pad(passport_no, 9)
    passport_cd = check_digit(passport_no_p)
    dob_cd = check_digit(dob_yymmdd)
    expiry_cd = check_digit(expiry_yymmdd)
    personal_no_p = pad("", 14)
    personal_cd = check_digit(personal_no_p)

    composite_input = (passport_no_p + passport_cd + dob_yymmdd + dob_cd +
                        expiry_yymmdd + expiry_cd + personal_no_p + personal_cd)
    composite_cd = check_digit(composite_input)

    line2 = (passport_no_p + passport_cd + nationality + dob_yymmdd + dob_cd +
              sex + expiry_yymmdd + expiry_cd + personal_no_p + personal_cd + composite_cd)
    line2 = pad(line2, 44)
    return line1, line2

def load_font(candidates, size):
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    print(f"WARNING: none of {candidates} found, using tiny default font.")
    return ImageFont.load_default()

def generate_one(person, index):
    W, H = 1000, 650
    img = Image.new("RGB", (W, H), color=(235, 235, 225))
    draw = ImageDraw.Draw(img)

    font_regular = load_font(["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"], 22)
    font_bold = load_font(["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"], 28)
    font_mrz = load_font(["consola.ttf", "cour.ttf", "Courier New.ttf", "DejaVuSansMono.ttf"], 30)

    draw.text((30, 20), "REPUBLIC OF INDIA / PASSPORT", font=font_bold, fill=(20, 20, 80))
    draw.rectangle([(20, 10), (W - 20, H - 10)], outline=(20, 20, 80), width=3)
    draw.rectangle([(40, 90), (240, 320)], outline=(0, 0, 0), width=2)
    draw.text((70, 190), "PHOTO", font=font_regular, fill=(120, 120, 120))

    surname = person["surname"]
    given_names = person["given_names"]
    passport_no = person["passport_no"]
    nationality = person["nationality"]
    dob_yymmdd = person["dob"]
    sex = person["sex"]
    expiry_yymmdd = person["expiry"]

    dob_iso = yymmdd_to_iso(dob_yymmdd, is_dob=True)
    expiry_iso = yymmdd_to_iso(expiry_yymmdd, is_dob=False)

    fields_display = [
        ("Surname", surname),
        ("Given Name(s)", given_names),
        ("Passport No.", passport_no),
        ("Nationality", "INDIAN"),
        ("Date of Birth", dob_iso),
        ("Sex", sex),
        ("Date of Expiry", expiry_iso),
    ]
    y = 90
    for label, value in fields_display:
        draw.text((270, y), f"{label}:", font=font_regular, fill=(0, 0, 0))
        draw.text((520, y), value, font=font_regular, fill=(0, 0, 50))
        y += 40

    line1, line2 = build_passport_mrz(surname, given_names, passport_no,
                                        nationality, dob_yymmdd, sex, expiry_yymmdd)

    mrz_y = H - 130
    draw.rectangle([(20, mrz_y - 15), (W - 20, H - 20)], fill=(255, 255, 255))
    draw.text((40, mrz_y), line1, font=font_mrz, fill=(0, 0, 0))
    draw.text((40, mrz_y + 45), line2, font=font_mrz, fill=(0, 0, 0))

    img_filename = f"clean_passport_{index:02d}.jpg"
    json_filename = f"clean_passport_{index:02d}.json"
    img_path = os.path.join(OUTPUT_DIR, img_filename)
    json_path = os.path.join(OUTPUT_DIR, json_filename)

    img.save(img_path, quality=95)

    ground_truth = {
        "filename": img_filename,
        "doc_type": "passport",
        "source": "self-generated synthetic fixture (NOT from MIDV-500 dataset)",
        "fields": {
            "surname": surname,
            "given_names": given_names,
            "passport_number": passport_no,
            "nationality": nationality,
            "date_of_birth": dob_iso,
            "sex": sex,
            "date_of_expiry": expiry_iso
        },
        "mrz": {
            "line1": line1,
            "line2": line2
        }
    }
    with open(json_path, "w") as f:
        json.dump(ground_truth, f, indent=2)

    return img_filename, json_filename, passport_no

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results = []
    for i, person in enumerate(SAMPLE_PEOPLE[:N_FIXTURES], start=1):
        img_f, json_f, pno = generate_one(person, i)
        results.append((img_f, json_f, pno))
        print(f"Created: {img_f} + {json_f}  (passport_no={pno})")

    print(f"\nDone. {len(results)} clean fixtures created in '{OUTPUT_DIR}/'")