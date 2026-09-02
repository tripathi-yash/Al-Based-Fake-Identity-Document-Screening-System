"""
Unit tests for Module 4 - Face Verification.
Real tests should run against data/fixtures/faces/matched/ (expect status="match")
and data/fixtures/faces/mismatched/ (expect status="mismatch").
"""
import pytest


def test_stub_returns_expected_schema():
    from modules.module4_face.stub import run_face_verification

    result = run_face_verification(b"fake_doc_bytes", b"fake_selfie_bytes")
    assert result["module"] == "face_verification"
    assert result["status"] in ("match", "mismatch", "no_face_detected")


# TODO: once face_verification.py is implemented:
# - test_matched_pair_returns_match()
# - test_mismatched_pair_returns_mismatch()
# - test_no_face_in_image_returns_no_face_detected_not_exception()
# - test_similarity_is_null_when_no_face_detected()
