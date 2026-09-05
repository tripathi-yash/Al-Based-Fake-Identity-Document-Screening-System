"""
Day 2 mock stub for Module 2 - Document Validation.
Real implementation in document_validation.py, same signature/schema.
"""


def run_validation(ocr_result: dict, doc_type: str) -> dict:
    return {
        "module": "document_validation",
        "status": "success",
        "checksum_pass": True,
        "text_mrz_match": True,
        "expiry_valid": True,
        "db_status": "clear",
        "flags": [],
    }