
"""
Debug EasyOCR output for the English passport fixture.

This script does not modify Module 1.
It prints:
1. Raw EasyOCR detections
2. Bounding boxes
3. Confidence scores
4. Current Module 1 extraction result
"""

from pathlib import Path

import cv2
import numpy as np

from backend.modules.module1_ocr import ocr_extraction as ocr


IMAGE_PATH = Path("data/fixtures/clean/clean_passport_02.jpg")


def main():
    print("=" * 80)
    print("PASSPORT OCR DEBUG")
    print("=" * 80)

    if not IMAGE_PATH.exists():
        print(f"ERROR: Image not found: {IMAGE_PATH}")
        return

    print(f"Image: {IMAGE_PATH}")
    print(f"OCR backend: {ocr._OCR_BACKEND}")
    print(f"OCR engine available: {ocr._OCR_ENGINE is not None}")
    print()

    # ------------------------------------------------------------------
    # Load image
    # ------------------------------------------------------------------
    image_bytes = IMAGE_PATH.read_bytes()

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        print("ERROR: Could not decode image.")
        return

    # Use the same preprocessing used by Module 1.
    image = ocr.preprocess_for_ocr(image)

    # ------------------------------------------------------------------
    # Raw EasyOCR detections
    # ------------------------------------------------------------------
    print("=" * 80)
    print("RAW OCR DETECTIONS")
    print("=" * 80)

    if ocr._OCR_BACKEND != "easyocr":
        print(f"ERROR: Expected EasyOCR but backend is {ocr._OCR_BACKEND}")
        return

    detections = ocr._OCR_ENGINE.readtext(
        image,
        detail=1,
        paragraph=False,
        mag_ratio=1.5,
    )

    for i, detection in enumerate(detections, start=1):
        bbox, text, confidence = detection

        xs = [point[0] for point in bbox]
        ys = [point[1] for point in bbox]

        x1 = min(xs)
        y1 = min(ys)
        x2 = max(xs)
        y2 = max(ys)

        print(
            f"{i:02d}: "
            f"text={text!r} | "
            f"confidence={confidence:.3f} | "
            f"bbox=({x1:.0f},{y1:.0f})-({x2:.0f},{y2:.0f})"
        )

    # ------------------------------------------------------------------
    # Current Module 1 result
    # ------------------------------------------------------------------
    print()
    print("=" * 80)
    print("CURRENT MODULE 1 RESULT")
    print("=" * 80)

    result = ocr.run_ocr(
        image_bytes,
        "passport",
    )

    print(result)

    print()
    print("=" * 80)
    print("END DEBUG")
    print("=" * 80)


if __name__ == "__main__":
    main()
