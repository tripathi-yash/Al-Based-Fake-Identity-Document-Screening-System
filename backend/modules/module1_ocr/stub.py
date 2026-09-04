"""
stub.py — Module 1 (OCR Extraction), Day-2 mock stub.

Per Section 9a ("Mock-First Integration Strategy"): every module owner
writes a stub with the SAME function name and signature the real
implementation will eventually have, returning the exact standardized mock
output from Section 9b, unmodified, no real OCR/CV code yet. Backend wires
this into the full pipeline on Day 2-3; from Day 3 onward, ocr_extraction.py
replaces this stub in-place with zero changes required anywhere else,
because the output schema never changes.

Do not add real logic here — that's ocr_extraction.py's job.
"""

from typing import Optional


def extract_ocr(image_path: str, doc_type: str, config: Optional[dict] = None) -> dict:
    """Same signature as ocr_extraction.extract_ocr(). Returns the literal,
    hardcoded Section 9b contract regardless of input, so the rest of the
    pipeline (Module 2 onward) can be built and tested against it before
    real OCR exists.
    """
    return {
        "module": "ocr_extraction",
        "doc_type": "passport",
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


def extract_ocr_failed(image_path: str, doc_type: str, config: Optional[dict] = None) -> dict:
    """Optional second stub for exercising the pipeline's failure path
    (Section 13: 'every module must return a defined failure state, never
    let an unhandled exception break the pipeline'). Not part of the
    Section 9b contract itself — a convenience for integration testing."""
    return {
        "module": "ocr_extraction",
        "doc_type": doc_type,
        "status": "failed",
        "extracted_fields": {},
    }
