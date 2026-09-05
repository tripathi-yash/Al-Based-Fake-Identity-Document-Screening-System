"""
Unit tests for Module 1 - OCR Extraction, against the REAL
modules/module1_ocr/ocr_extraction.py (not stub.py — the old test file
pointed at backend.modules.module1_ocr.stub, which no longer matches
your project layout or the real implementation).

Two layers of tests here:
  1. Contract tests that don't need a real image (garbage bytes / unknown
     doc_type) — these are deterministic regardless of whether
     PaddleOCR/EasyOCR/pytesseract is installed.
  2. Real-fixture tests (skipped automatically if the fixture file isn't
     found at the path below) — adjust FIXTURES_DIR to match your layout.
"""
import os
import re
import pytest

from backend.modules.module1_ocr.ocr_extraction import run_ocr

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures")
CLEAN_PASSPORT = os.path.join(FIXTURES_DIR, "clean", "clean_passport_01.jpg")

ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

skip_if_missing = pytest.mark.skipif(
    not os.path.isfile(CLEAN_PASSPORT),
    reason=f"Fixture not found at {CLEAN_PASSPORT} — adjust FIXTURES_DIR at top of this file",
)


# ---------------------------------------------------------------------------
# Contract tests — no real image needed, always runnable
# ---------------------------------------------------------------------------
def test_unknown_doc_type_fails_without_guessing():
    """run_ocr must return failed immediately for an unregistered doc_type,
    per the module's own docstring: 'unknown doc_type -> failed, don't guess'."""
    result = run_ocr(b"irrelevant bytes", "not_a_real_doc_type")
    assert result["status"] == "failed"
    assert result["extracted_fields"] == {}


def test_garbage_bytes_never_raises_and_fails_gracefully():
    """Section 9b/13 hard rule: never raise out of run_ocr() for a bad image."""
    result = run_ocr(b"this is not a valid jpeg", "passport")
    assert result["status"] == "failed"
    assert result["extracted_fields"] == {}


def test_empty_bytes_never_raises():
    result = run_ocr(b"", "passport")
    assert result["status"] in ("failed", "partial", "success")  # must not raise


def test_output_always_has_required_top_level_keys():
    result = run_ocr(b"garbage", "passport")
    for key in ("module", "doc_type", "status", "extracted_fields"):
        assert key in result
    assert result["module"] == "ocr_extraction"
    assert result["status"] in ("success", "partial", "failed")


# ---------------------------------------------------------------------------
# Real-fixture tests — require an actual image + at least one OCR backend
# installed (paddleocr / easyocr / pytesseract). If no backend is
# installed, extracted_fields may come back mostly empty via the MRZ path
# only (if passporteye is present) — these tests check STRUCTURE and
# ISO date formatting, not that every field was found, since OCR accuracy
# depends on your environment's installed engines.
# ---------------------------------------------------------------------------
@skip_if_missing
def test_clean_passport_returns_some_extracted_fields():
    with open(CLEAN_PASSPORT, "rb") as f:
        image_bytes = f.read()
    result = run_ocr(image_bytes, "passport")
    assert result["status"] in ("success", "partial"), (
        f"Expected success/partial on a clean fixture, got '{result['status']}' — "
        "check that an OCR backend (paddleocr/easyocr/pytesseract) is installed."
    )
    assert len(result["extracted_fields"]) > 0


@skip_if_missing
def test_every_extracted_field_has_value_and_confidence_in_range():
    with open(CLEAN_PASSPORT, "rb") as f:
        image_bytes = f.read()
    result = run_ocr(image_bytes, "passport")
    for field_name, field in result["extracted_fields"].items():
        assert "value" in field, f"Field '{field_name}' missing 'value'"
        assert "confidence" in field, f"Field '{field_name}' missing 'confidence'"
        assert 0.0 <= field["confidence"] <= 1.0, \
            f"Field '{field_name}' confidence out of range: {field['confidence']}"


@skip_if_missing
def test_dates_are_iso_8601_when_present():
    """Hard rule: dates are always ISO 8601 (YYYY-MM-DD), never MRZ raw YYMMDD."""
    with open(CLEAN_PASSPORT, "rb") as f:
        image_bytes = f.read()
    result = run_ocr(image_bytes, "passport")
    for date_field in ("dob", "expiry"):
        if date_field in result["extracted_fields"]:
            value = result["extracted_fields"][date_field]["value"]
            assert ISO_DATE_PATTERN.match(value), f"{date_field} not ISO 8601: {value}"


@skip_if_missing
def test_mrz_raw_present_when_mrz_successfully_parsed():
    with open(CLEAN_PASSPORT, "rb") as f:
        image_bytes = f.read()
    result = run_ocr(image_bytes, "passport")
    if "mrz_raw" in result:
        assert "line1" in result["mrz_raw"]
        assert "line2" in result["mrz_raw"]
        assert len(result["mrz_raw"]["line2"]) == 44, "TD3 line2 must be 44 chars"