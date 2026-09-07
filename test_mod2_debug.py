# """
# Quick manual test: feed the REAL Module 1 output (from clean_passport_02.jpg,
# captured in the last successful run) straight into Module 2, no mocking.
# """
# from backend.modules.module2_validation.document_validation import run_validation

# # Exact ocr_result from the last successful Module 1 run — copy-pasted,
# # not hand-built, so this is a true integration check.
# ocr_result = {
#     'module': 'ocr_extraction',
#     'doc_type': 'passport',
#     'status': 'success',
#     'extracted_fields': {
#         'name': {'value': 'VERMA PRIYA', 'confidence': 0.67},
#         'passport_number': {'value': 'N2345678', 'confidence': 0.67},
#         'nationality': {'value': 'IND', 'confidence': 0.67},
#         'dob': {'value': '1999-01-12', 'confidence': 0.67},
#         'expiry': {'value': '2029-03-12', 'confidence': 0.67},
#         'gender': {'value': 'F', 'confidence': 0.67},
#     },
#     'mrz_raw': {
#         'line1': 'P<INDVERMA<<PRIYA<<<<<<<<<<<<<<<<<<<<<<<<<<<',
#         'line2': 'N2345678<2IND9901122F2903127<<<<<<<<<<<<<<04',
#     },
# }

# result = run_validation(ocr_result, "passport")

# print("=" * 60)
# print("MODULE 2 RESULT")
# print("=" * 60)
# for key, value in result.items():
#     print(f"{key}: {value}")

"""
True integration test: Module 1's REAL return value is passed directly
into Module 2 — no hand-copied dict in between. This is the actual
proof that ocr_result -> run_validation() wiring works, matching exactly
what routes.py does in the real /screen pipeline.
"""
import os

from backend.modules.module1_ocr.ocr_extraction import run_ocr
from backend.modules.module2_validation.document_validation import run_validation

IMAGE_PATH = os.path.join(
    os.path.dirname(__file__),
    "data", "fixtures", "clean", "clean_passport_02.jpg",
)

with open(IMAGE_PATH, "rb") as f:
    image_bytes = f.read()

# --- Module 1: real call, no mocking ---
ocr_result = run_ocr(image_bytes, "passport")

print("=" * 60)
print("MODULE 1 OUTPUT (live)")
print("=" * 60)
for key, value in ocr_result.items():
    print(f"{key}: {value}")

# --- Module 2: fed directly from Module 1's actual return value ---
validation_result = run_validation(ocr_result, "passport")

print()
print("=" * 60)
print("MODULE 2 OUTPUT (fed from live Module 1 result above)")
print("=" * 60)
for key, value in validation_result.items():
    print(f"{key}: {value}")