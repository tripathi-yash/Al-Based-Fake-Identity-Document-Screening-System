"""
Day 2 mock stub for Module 1 - OCR Extraction.
Real implementation goes in ocr_extraction.py, same function signature,
same return schema (see schema/module_io_schema.json -> module1_ocr_extraction).
Keep this stub file forever as a fallback / demo safety net.
"""


def run_ocr(doc_image_bytes: bytes, doc_type: str) -> dict:
    return {
        "module": "ocr_extraction",
        "doc_type": doc_type,
        "status": "success",
        "extracted_fields": {
            "name": {"value": "JOHN DOE", "confidence": 0.95},
            "passport_number": {"value": "P1234567", "confidence": 0.97},
            "nationality": {"value": "IND", "confidence": 0.92},
            "dob": {"value": "1988-05-04", "confidence": 0.94},
            "expiry": {"value": "2030-01-15", "confidence": 0.96},
            "gender": {"value": "M", "confidence": 0.90},
        },
        "mrz_raw": {
            "line1": "P<INDDOE<<JOHN<<<<<<<<<<<<<<<<<<<<<<<<<<<<<",
            "line2": "P1234567<4IND8805042M3001158<<<<<<<<<<<<<<08",
        },
    }