"""
Unit tests for Module 2 - Document Validation, against the REAL
modules/module2_validation/document_validation.py.

Per Sahil's stated testing preference (isolated tests using hand-built
mock OCR results before touching real images), these tests construct
Module 1-shaped dicts by hand rather than depending on the OCR engine —
that keeps this file deterministic and fast regardless of what OCR
backends are installed.

Checksum values below are taken directly from clean_passport_01.json's
actual MRZ line 2 (N1234567<7IND0308153M3008155<<<<<<<<<<<<<<06), which
is real fixture data, not invented:
    doc_number=N1234567<  check=7
    dob=030815            check=3
    expiry=300815         check=5
    composite check=6
This file only asserts True/False via verify_check_digit /
verify_composite_check (the actual functions document_validation.py
imports) — it does not assume how those functions compute a digit
internally, since checksum.py's source wasn't available when writing this.
"""
import pytest

from backend.modules.module2_validation.checksum import verify_check_digit, verify_composite_check
from backend.modules.module2_validation.document_validation import (
    document_validation,
    run_validation,
    parse_td3_line2,
    text_mrz_crosscheck,
    mrz_checksum_results,
    is_expiry_valid,
)

REAL_MRZ_LINE2 = "N1234567<7IND0308153M3008155<<<<<<<<<<<<<<06"


# ---------------------------------------------------------------------------
# Checksum — verified against real fixture MRZ, not invented values
# ---------------------------------------------------------------------------
def test_known_good_doc_number_checksum_passes():
    assert verify_check_digit("N1234567<", "7") is True


def test_known_good_dob_checksum_passes():
    assert verify_check_digit("030815", "3") is True


def test_known_good_expiry_checksum_passes():
    assert verify_check_digit("300815", "5") is True


def test_deliberately_wrong_checksum_fails():
    assert verify_check_digit("N1234567<", "9") is False


def test_full_mrz_checksum_results_on_real_line():
    parsed = parse_td3_line2(REAL_MRZ_LINE2)
    assert parsed is not None
    overall_pass, flags = mrz_checksum_results(parsed)
    assert overall_pass is True
    assert flags == []


def test_mrz_checksum_results_flags_tampered_line():
    """Simulates tampered_02_dob_alter: DOB field on the printed side was
    changed but the MRZ digits were left untouched at the source — here we
    corrupt the MRZ dob digit itself to prove the flag mechanism works."""
    tampered_line2 = "N1234567<7IND9999993M3008155<<<<<<<<<<<<<<06"
    parsed = parse_td3_line2(tampered_line2)
    assert parsed is not None
    overall_pass, flags = mrz_checksum_results(parsed)
    assert overall_pass is False
    assert "checksum_fail_dob" in flags


# ---------------------------------------------------------------------------
# Text vs MRZ cross-check — this is the actual tampered_02_dob_alter catch
# ---------------------------------------------------------------------------
def test_text_mrz_crosscheck_passes_when_consistent():
    parsed = parse_td3_line2(REAL_MRZ_LINE2)
    extracted_fields = {
        "passport_number": {"value": "N1234567", "confidence": 0.95},
        "dob": {"value": "2003-08-15", "confidence": 0.9},
        "expiry": {"value": "2030-08-15", "confidence": 0.9},
        "nationality": {"value": "IND", "confidence": 0.9},
    }
    match_pass, flags = text_mrz_crosscheck(extracted_fields, parsed, "passport_number")
    assert match_pass is True
    assert flags == []


def test_text_mrz_crosscheck_catches_dob_alter():
    """This IS tampered_02_dob_alter's documented catch: printed DOB says
    1990-01-01 but MRZ (unchanged) still says 2003-08-15."""
    parsed = parse_td3_line2(REAL_MRZ_LINE2)
    extracted_fields = {
        "passport_number": {"value": "N1234567", "confidence": 0.95},
        "dob": {"value": "1990-01-01", "confidence": 0.9},  # altered on the printed side
        "expiry": {"value": "2030-08-15", "confidence": 0.9},
        "nationality": {"value": "IND", "confidence": 0.9},
    }
    match_pass, flags = text_mrz_crosscheck(extracted_fields, parsed, "passport_number")
    assert match_pass is False
    assert "text_mrz_mismatch_dob" in flags


# ---------------------------------------------------------------------------
# Full document_validation() / run_validation() — hand-built Module 1 output
# ---------------------------------------------------------------------------
def _make_ocr_result(doc_type="passport", dob_value="2003-08-15", passport_number="N1234567"):
    return {
        "module": "ocr_extraction",
        "doc_type": doc_type,
        "status": "success",
        "extracted_fields": {
            "name": {"value": "SHARMA ASHRAY KUMAR", "confidence": 0.95},
            "passport_number": {"value": passport_number, "confidence": 0.97},
            "nationality": {"value": "IND", "confidence": 0.92},
            "dob": {"value": dob_value, "confidence": 0.94},
            "expiry": {"value": "2030-08-15", "confidence": 0.96},
            "gender": {"value": "M", "confidence": 0.9},
        },
        "mrz_raw": {
            "line1": "P<INDSHARMA<<ASHRAY<KUMAR<<<<<<<<<<<<<<<<<<<",
            "line2": REAL_MRZ_LINE2,
        },
    }


def test_upstream_ocr_failed_short_circuits():
    failed_ocr = {"status": "failed", "extracted_fields": {}}
    result = document_validation(failed_ocr)
    assert result["status"] == "failed"
    assert "upstream_ocr_failed" in result["flags"]


def test_unknown_doc_type_flagged():
    ocr_result = _make_ocr_result(doc_type="totally_unknown_type")
    result = document_validation(ocr_result)
    assert "unknown_doc_type" in result["flags"]


def test_clean_document_passes_checksum_and_crosscheck():
    ocr_result = _make_ocr_result()
    result = document_validation(ocr_result)
    assert result["checksum_pass"] is True
    assert result["text_mrz_match"] is True
    # N1234567 is not in ISSUANCE_TABLE in the version of mock_db1 shown to
    # me — if you've since added it, update this assertion to "clear".
    assert result["db_status"] in ("clear", "not_found")


def test_dob_altered_document_fails_crosscheck_but_not_checksum():
    """The exact tampered_02_dob_alter scenario, reproduced with hand-built
    Module 1 output instead of depending on real OCR + real image."""
    ocr_result = _make_ocr_result(dob_value="1990-01-01")
    result = document_validation(ocr_result)
    assert result["checksum_pass"] is True  # MRZ itself untouched
    assert result["text_mrz_match"] is False  # THIS is the catch
    assert "text_mrz_mismatch_dob" in result["flags"]


def test_run_validation_entry_point_matches_routes_usage():
    """routes.py calls run_validation(ocr_result, doc_type) — confirm that
    exact call signature works end to end."""
    ocr_result = _make_ocr_result()
    result = run_validation(ocr_result, "passport")
    assert result["status"] == "success"


def test_mrz_format_none_returns_null_checksum():
    """driving_license has mrz_format='none' — checksum_pass/text_mrz_match
    must be null (None) per schema, not False."""
    ocr_result = {
        "module": "ocr_extraction",
        "doc_type": "driving_license",
        "status": "success",
        "extracted_fields": {
            "name": {"value": "JOHN DOE", "confidence": 0.9},
            "license_number": {"value": "DL1234", "confidence": 0.9},
            "dob": {"value": "1995-01-01", "confidence": 0.9},
            "expiry": {"value": "2028-01-01", "confidence": 0.9},
        },
    }
    result = document_validation(ocr_result)
    assert result["checksum_pass"] is None
    assert result["text_mrz_match"] is None