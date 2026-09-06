
# import cv2

# from backend.modules.module1_ocr.ocr_extraction import (
#     _OCR_BACKEND,
#     _OCR_ENGINE,
#     _ocr_text_lines,
# )


# IMAGE_PATH = (
#     "data/fixtures/clean/"
#     "23_fin_drvlic/images/CA/CA23_01.jpg"
# )


# image = cv2.imread(IMAGE_PATH)

# print("=" * 70)
# print("FINNISH MIDV-500 DRIVER LICENSE OCR DEBUG")
# print("=" * 70)

# print("Image loaded:", image is not None)

# if image is None:
#     raise RuntimeError(
#         f"Could not load image: {IMAGE_PATH}"
#     )

# print("Image shape:", image.shape)
# print("OCR backend:", _OCR_BACKEND)
# print("OCR engine available:", _OCR_ENGINE is not None)

# print("\n" + "=" * 70)
# print("RAW OCR TEXT")
# print("=" * 70)

# lines = _ocr_text_lines(image)

# if not lines:
#     print("NO TEXT DETECTED")
# else:
#     for i, line in enumerate(lines, start=1):
#         print(f"{i:02d}: {line!r}")

# print("\n" + "=" * 70)
# print("END")
# print("=" * 70)

import cv2

from backend.modules.module1_ocr.ocr_extraction import (
    _OCR_BACKEND,
    _OCR_ENGINE,
)


IMAGE_PATH = (
    "data/fixtures/clean/"
    "23_fin_drvlic/images/CA/CA23_01.jpg"
)


image = cv2.imread(IMAGE_PATH)

print("=" * 80)
print("FINNISH MIDV-500 DRIVER LICENSE - DETAILED OCR DEBUG")
print("=" * 80)

print("Image loaded:", image is not None)
print("Image shape:", image.shape if image is not None else None)
print("OCR backend:", _OCR_BACKEND)
print("OCR engine available:", _OCR_ENGINE is not None)


if image is None:
    raise RuntimeError(f"Could not load image: {IMAGE_PATH}")


if _OCR_ENGINE is None:
    raise RuntimeError("EasyOCR engine is not available.")


print("\n" + "=" * 80)
print("DETAILED OCR DETECTIONS")
print("=" * 80)

results = _OCR_ENGINE.readtext(image, detail=1)

if not results:
    print("NO TEXT DETECTED")
else:
    for i, item in enumerate(results, start=1):
        bbox, text, confidence = item

        xs = [point[0] for point in bbox]
        ys = [point[1] for point in bbox]

        x1 = int(min(xs))
        y1 = int(min(ys))
        x2 = int(max(xs))
        y2 = int(max(ys))

        print(
            f"{i:02d}: "
            f"text={text!r} | "
            f"confidence={confidence:.3f} | "
            f"bbox=({x1},{y1})-({x2},{y2})"
        )


print("\n" + "=" * 80)
print("END")
print("=" * 80)