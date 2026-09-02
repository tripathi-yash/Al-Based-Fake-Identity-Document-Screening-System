"""
Unit tests for Module 2 - Document Validation.
Checksum math should be tested independently since it's pure, deterministic logic.
"""
import pytest


def test_stub_returns_expected_schema():
    from modules.module2_validation.stub import run_validation

    result = run_validation({}, "passport")
    assert result["module"] == "document_validation"
    assert result["db_status"] in ("clear", "blacklisted", "expired", "not_found")
    assert isinstance(result["flags"], list)


def test_checksum_known_value():
    from modules.module2_validation.checksum import compute_check_digit

    # TODO: replace with a real ICAO 9303 worked example once checksum.py is filled in
    # e.g. compute_check_digit("D231458907") should equal a known correct digit
    pass


# TODO: once document_validation.py is implemented:
# - test_expired_document_flagged()
# - test_blacklisted_document_flagged()
# - test_text_mrz_mismatch_flagged()
# - test_mrz_format_none_returns_null_checksum_pass()  # driving license / permit case
