"""
Module 1 — OCR Extraction

Converts a document image into structured field data (name, passport no.,
DOB, expiry, nationality, gender, visa fields, etc.), per Section 4 of the
action plan.

Public API:
    extract_ocr(image_path, doc_type, config=None) -> dict
        The real pipeline (OpenCV preprocessing + MRZ parsing + visual-zone
        OCR), config-driven per doc_types_config.json (Section 11). This is
        what Module 2 (and the rest of the pipeline) should import from
        Day 3 onward.

    stub.extract_ocr(image_path, doc_type, config=None) -> dict
        The Day-2 hardcoded mock with the identical signature and output
        shape, for wiring up the rest of the pipeline before real OCR exists
        (Section 9a). Swapping stub -> real requires no changes elsewhere.

    parse_mrz(mrz_lines, mrz_format) -> ParsedMRZ | None
        Lower-level MRZ structural parser (TD3 / TD1), re-exported for
        anything that needs raw MRZ fields directly (e.g. Module 2's
        text/MRZ cross-check).

    load_config(path=None) -> dict
        Loads doc_types_config.json (Section 11), the shared source of
        truth for per-doc-type field layout and MRZ format.

Output contract: every call returns the Section 9b shape —
    {
      "module": "ocr_extraction",
      "doc_type": ...,
      "status": "success" | "partial" | "failed",
      "extracted_fields": {field: {"value": ..., "confidence": 0.0-1.0}, ...},
      "mrz_raw": {"line1": ..., "line2": ..., ["line3": ...]}   # when MRZ present
    }
This function never raises — a bad image yields status="failed", not an
exception (Section 13).
"""

from .ocr_extraction import extract_ocr, load_config, preprocess_image, extract_mrz
from .mrz_parser import parse_mrz, parse_td3, parse_td1, compute_check_digit, ParsedMRZ, MRZField
from . import stub

__all__ = [
    "extract_ocr",
    "load_config",
    "preprocess_image",
    "extract_mrz",
    "parse_mrz",
    "parse_td3",
    "parse_td1",
    "compute_check_digit",
    "ParsedMRZ",
    "MRZField",
    "stub",
]
