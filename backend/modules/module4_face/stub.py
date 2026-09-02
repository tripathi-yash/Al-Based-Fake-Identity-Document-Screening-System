"""
Day 2 mock stub for Module 4 - Face Verification.
Real implementation in face_verification.py, same signature/schema.
"""


def run_face_verification(doc_image_bytes: bytes, live_selfie_bytes: bytes) -> dict:
    return {
        "module": "face_verification",
        "status": "match",
        "similarity": 0.87,
        "threshold_used": 0.6,
        "face_detected_in_document": True,
        "face_detected_in_live": True,
    }
