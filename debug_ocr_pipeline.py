"""
Isolated OCR pipeline debug — bypasses ocr_extraction.py's exception
handling entirely so real errors surface, and tests each pipeline stage
separately to find exactly where text recognition breaks down.

Run from project root:
    python debug_ocr_pipeline.py
"""
import os
import cv2
import numpy as np
import easyocr

# data\fixtures\clean\23_fin_drvlic\images\CA\CA23_01.jpg
# IMAGE_PATH = os.path.join(
#     os.path.dirname(__file__),
#     "data",
#     "fixtures",
#     "clean",
#     "23_fin_drvlic",
#     "images",
#     "CA",
#     "CA23_01.jpg"
# )

IMAGE_PATH = os.path.join(
    os.path.dirname(__file__),
    "data",
    "fixtures",
    "clean",
    "25_grc_passport",
    "images",
    "CA",
    "CA25_01.jpg"
)

# IMAGE_PATH = os.path.join(
#     os.path.dirname(__file__),
#     "data",
#     "fixtures",
#     "clean",
#     "clean_passport_01.jpg"
# )

# data\fixtures\clean\23_fin_drvlic\images\CA\CA23_01.jpg
print("IMAGE_PATH =", IMAGE_PATH)
print("EXISTS =", os.path.exists(IMAGE_PATH))

with open(IMAGE_PATH, "rb") as f:
    image_bytes = f.read()

arr = np.frombuffer(image_bytes, dtype=np.uint8)
image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
print(f"Image decoded: {image is not None}, shape={image.shape if image is not None else None}")

reader = easyocr.Reader(["en"], gpu=False)
reader = easyocr.Reader(["en"], gpu=False)

image = cv2.imread(IMAGE_PATH)

print("Image shape:", image.shape)

# Diagnostic crop based on the detected MRZ bounding-box region
mrz_debug = image[900:1200, 0:1080]
cv2.imwrite("debug_detected_mrz_region.jpg", mrz_debug)

print("Saved debug_detected_mrz_region.jpg")
# ============================================================
# MRZ LOCATION TEST
# ============================================================

print("\n" + "=" * 70)
print("MRZ LOCATION TEST")
print("=" * 70)

detections = reader.readtext(image, detail=1)

for bbox, text, conf in detections:
    cleaned = "".join(
        c for c in text.upper()
        if c.isalnum() or c == "<"
    )

    if "<" in cleaned or len(cleaned) >= 20:
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]

        print(
            f"text={text!r} | "
            f"cleaned={cleaned!r} | "
            f"conf={conf:.3f} | "
            f"bbox=({min(xs):.0f},{min(ys):.0f})"
            f"-({max(xs):.0f},{max(ys):.0f})"
        )
# ---------------------------------------------------------------------
# Test 1: raw image, no preprocessing, no cropping — simplest possible case
# ---------------------------------------------------------------------
print("\n" + "=" * 70)
print("TEST 1: RAW image, full frame, no preprocessing")
print("=" * 70)
raw_text = reader.readtext(image, detail=0)
print(raw_text)

# ---------------------------------------------------------------------
# Test 2: MRZ band crop, exactly as ocr_extraction.py's extract_mrz() does it
# ---------------------------------------------------------------------
print("\n" + "=" * 70)
print("TEST 2: RAW image, MRZ band crop (bottom 25%)")
print("=" * 70)
# h, w = image.shape[:2]
# band = image[int(h * 0.75):h, 0:w]
# band_text = reader.readtext(band, detail=0)
# print(band_text)
# cv2.imwrite("debug_mrz_band_crop.jpg", band)
h, w = image.shape[:2]

bands = {
    "bottom_40": image[int(h * 0.60):h, 0:w],
    "bottom_35": image[int(h * 0.65):h, 0:w],
    "bottom_30": image[int(h * 0.70):h, 0:w],
    "bottom_25": image[int(h * 0.75):h, 0:w],
    "bottom_20": image[int(h * 0.80):h, 0:w],
}

for name, band in bands.items():
    print("\n" + "=" * 70)
    print(name, band.shape)
    print("=" * 70)

    text = reader.readtext(band, detail=0)
    print(text)

    cv2.imwrite(f"debug_{name}.jpg", band)

print("(saved debug_mrz_band_crop.jpg — open it and check the MRZ text is actually inside this crop)")

# ---------------------------------------------------------------------
# Test 3: full image AFTER preprocess_for_ocr() — this is the suspect.
# correct_geometry() uses Otsu threshold + minAreaRect to estimate skew,
# a technique built for scanned pages with a clear foreground silhouette.
# On a full-frame rendered card (text everywhere, no distinct page
# boundary), this can produce a wrong rotation and garble the image.
# ---------------------------------------------------------------------
print("\n" + "=" * 70)
# print("TEST 3: image AFTER preprocess_for_ocr() (deskew + contrast normalize)")
print("TEST 3: image AFTER preprocess_for_ocr() (only contrast normalize)")
print("=" * 70)
print("\n" + "=" * 70)
print("TEST 3: image AFTER preprocess_for_ocr()")
print("=" * 70)

from backend.preprocessing.image_preprocess import preprocess_for_ocr

processed = preprocess_for_ocr(image)

print("Original shape :", image.shape)
print("Processed shape:", processed.shape)

# Save completely different filenames so there can be no stale-file confusion.
cv2.imwrite("DEBUG_ORIGINAL.jpg", image)
cv2.imwrite("DEBUG_PROCESSED.jpg", processed)

# Compare actual pixel arrays.
print("Same shape:", image.shape == processed.shape)
print("Arrays identical:", np.array_equal(image, processed))

diff = cv2.absdiff(image, processed)
print("Mean pixel difference:", float(np.mean(diff)))
print("Max pixel difference :", int(np.max(diff)))

processed_text = reader.readtext(processed, detail=0)
print(processed_text)
# try:
#     from backend.preprocessing.image_preprocess import preprocess_for_ocr
#     processed = preprocess_for_ocr(image)
#     print(
#     "Debug : \nProcessed shape:",
#     processed.shape,
#     "dtype:",
#     processed.dtype,
#     "min:",
#     processed.min(),
#     "max:",
#     processed.max(),
# )
    # cv2.imwrite("debug_after_preprocessing.jpg", processed)

    # print(
    #     "DEBUG : \nOriginal shape:",
    #     image.shape,
    #     "Processed shape:",
    #     processed.shape,
    # )
    # print("(saved debug_after_preprocessing.jpg — open it and visually compare to the original)")
    # processed_text = reader.readtext(processed, detail=0)
    # print(processed_text)
# except Exception as e:
#     print(f"preprocess_for_ocr import/run failed: {e}")

# print("\n" + "=" * 70)
# print("DIAGNOSIS:")
# print("- If Test 1 finds text but Test 3 finds nothing -> preprocess_for_ocr()")
# print("  is corrupting the image. Open debug_after_preprocessing.jpg to confirm")
# print("  visually (look for unexpected rotation/warping).")
# print("- If Test 1 also finds nothing -> the problem is EasyOCR itself or the")
# print("  image, not preprocessing. Open the original fixture and check it opens")
# print("  correctly outside Python too.")
# print("- If Test 1 works but Test 2 (band crop) finds nothing -> the 0.75")
# print("  crop ratio doesn't align with where the MRZ actually sits on this")
# print("  fixture. Open debug_mrz_band_crop.jpg to check.")
# print("=" * 70)
