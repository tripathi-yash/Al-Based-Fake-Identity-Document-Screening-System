"""
Unit tests for Module 1 - OCR Extraction.
Run against both stub.py (should always pass, sanity check) and the real
implementation once built. Use fixtures from data/fixtures/ + the manifest.
"""
import pytest


def test_stub_returns_expected_schema():
    from modules.module1_ocr.stub import run_ocr

    result = run_ocr(b"fake_bytes", "passport")
    assert result["module"] == "ocr_extraction"
    assert result["status"] in ("success", "partial", "failed")
    assert "name" in result["extracted_fields"]
    assert 0.0 <= result["extracted_fields"]["name"]["confidence"] <= 1.0


# TODO: once ocr_extraction.py is implemented, add tests against real fixtures:
# - test_mrz_parses_correctly_on_clean_passport()
# - test_confidence_drops_on_blurry_image()
# - test_dob_and_expiry_are_iso8601_format()
