"""
Unit tests for Module 2 - Document Validation.
Checksum math is tested independently since it's pure, deterministic logic --
verified here against a worked example from our own clean_passport_01 fixture,
which was itself independently confirmed valid using the official `mrz`
Python library earlier in this project.
"""
import pytest


def test_stub_returns_expected_schema():
    from backend.modules.module2_validation.stub import run_validation

    result = run_validation({}, "passport")
    assert result["module"] == "document_validation"
    assert result["db_status"] in ("clear", "blacklisted", "expired", "not_found")
    assert isinstance(result["flags"], list)


def test_checksum_known_value_passport_number():
    """Worked example: passport_number 'N1234567' (padded to 'N1234567<')
    from our clean_passport_01.json fixture has a verified check digit of 7."""
    from backend.modules.module2_validation.checksum import compute_check_digit

    assert compute_check_digit("N1234567<") == 7


def test_checksum_known_value_date_of_birth():
    """Worked example: DOB '030815' (2003-08-15) from clean_passport_01.json
    has a verified check digit of 3."""
    from backend.modules.module2_validation.checksum import compute_check_digit

    assert compute_check_digit("030815") == 3


def test_checksum_all_filler_is_zero():
    """A field of all '<' filler characters should always checksum to 0,
    since filler has value 0 regardless of position/weight."""
    from backend.modules.module2_validation.checksum import compute_check_digit

    assert compute_check_digit("<" * 14) == 0


# TODO: once document_validation.py is implemented:
# - test_expired_document_flagged()
# - test_blacklisted_document_flagged()
# - test_text_mrz_mismatch_flagged()
# - test_mrz_format_none_returns_null_checksum_pass()  # driving license / permit case