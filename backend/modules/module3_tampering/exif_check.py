"""
EXIF/metadata check — SUPPORTING evidence only.

Vulnerability, stated honestly (say this if asked in Q&A):
Metadata can be stripped entirely (WhatsApp, screenshots, most social
platforms do this to legitimate images) or forged. Absence of a suspicious
tag is NOT proof of authenticity — it only means this signal is silent,
not that the document is clean. This is exactly why it never gets veto
power in the fusion logic in tampering_detection.py.
"""
import io
from PIL import Image
from PIL.ExifTags import TAGS

EDITING_SOFTWARE_KEYWORDS = [
    "photoshop", "gimp", "paint.net", "affinity", "pixlr", "lightroom", "canva",
]


def check_exif(image_bytes: bytes) -> dict:
    img = Image.open(io.BytesIO(image_bytes))
    exif_raw = img._getexif() if hasattr(img, "_getexif") else None

    software = None
    date_time_original = None
    date_time_modified = None

    if exif_raw:
        tags = {TAGS.get(k, k): v for k, v in exif_raw.items()}
        software = tags.get("Software")
        date_time_original = tags.get("DateTimeOriginal")
        date_time_modified = tags.get("DateTime")

    editing_software_detected = None
    if software:
        for keyword in EDITING_SOFTWARE_KEYWORDS:
            if keyword.lower() in str(software).lower():
                editing_software_detected = software
                break

    # A modification timestamp meaningfully after the original capture
    # timestamp is a real secondary signal — implement the comparison once
    # you have real fixture EXIF data to test date formats against.
    modified_after_creation = bool(
        date_time_original and date_time_modified and date_time_original != date_time_modified
    )

    return {
        "editing_software_detected": editing_software_detected,
        "modified_after_creation": modified_after_creation,
        "raw_software_tag": software,
        "exif_present": exif_raw is not None,
    }

if __name__ == "__main__":
    import os
    import matplotlib.pyplot as plt

    example_path = os.path.join(
        os.path.dirname(__file__),
        "mantranet_lib",
        "Demo_images",
        "example4.jpg"
    )

    with open(example_path, "rb" ) as file:
        image_bytes = file.read()

    result = check_exif(image_bytes=image_bytes)

    print(result)
