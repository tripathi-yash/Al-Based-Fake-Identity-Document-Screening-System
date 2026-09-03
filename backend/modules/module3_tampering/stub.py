"""
Day 2 mock stub for Module 3 - Tampering Detection.
Updated to match the DL-primary + classical-supporting fusion schema
(see tampering_detection.py for the real implementation and rationale).
Keep this stub file forever as a fallback / demo safety net — e.g. if
ManTraNet fails to load right before the demo, swap the import back to
this stub and the pipeline keeps running.
"""


def run_tampering_detection(doc_image_bytes: bytes) -> dict:
    return {
        "module": "tampering_detection",
        "status": "success",
        "dl_tamper_probability": 0.08,
        "ela_score": 0.12,
        "ela_clarity": 0.88,
        "copy_move_flag": False,
        "exif_flag": False,
        "exif_details": {
            "editing_software_detected": None,
            "modified_after_creation": False,
            "raw_software_tag": None,
            "exif_present": True,
        },
        "overall_tamper_flag": False,
        "tamper_verdict": "clean",
        "supporting_flags": [],
    }
