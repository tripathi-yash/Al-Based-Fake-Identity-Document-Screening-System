"""
Unit tests for Module 3 - Tampering Detection.
Real tests should run against data/fixtures/clean/ (expect overall_tamper_flag=False)
and data/fixtures/tampered/ (expect overall_tamper_flag=True).
"""
import pytest


def test_stub_returns_expected_schema():
    from modules.module3_tampering.stub import run_tampering_detection

    result = run_tampering_detection(b"fake_bytes")
    assert result["module"] == "tampering_detection"
    assert 0.0 <= result["ela_score"] <= 1.0
    assert 0.0 <= result["ela_clarity"] <= 1.0
    assert isinstance(result["overall_tamper_flag"], bool)


# TODO: once ela.py / copy_move.py / exif_check.py are implemented:
# - test_clean_fixture_not_flagged()  -- uses data/fixtures/clean/, guards against ELA self-contamination
# - test_tampered_fixture_is_flagged()  -- uses data/fixtures/tampered/
# - test_low_clarity_on_recompressed_image()  -- degraded image should lower ela_clarity, not silently pass
