"""
Day 2 mock stub for Module 3 - Tampering Detection.
Real implementation combines ela.py + exif_check.py + copy_move.py into
tampering_detection.py, same signature/schema.
"""


def run_tampering_detection(doc_image_bytes: bytes) -> dict:
    return {
        "module": "tampering_detection",
        "status": "success",
        "ela_score": 0.12,
        "ela_clarity": 0.88,
        "copy_move_flag": False,
        "exif_flag": False,
        "exif_details": {"editing_software_detected": None, "modified_after_creation": False},
        "overall_tamper_flag": False,
    }
