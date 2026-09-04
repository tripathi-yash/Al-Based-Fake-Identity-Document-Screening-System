"""
Unit tests for Module 4 - Face Verification.
Real tests should run against data/fixtures/faces/matched/ (expect status="match")
and data/fixtures/faces/mismatched/ (expect status="mismatch").
"""
import pytest


def test_stub_returns_expected_schema():
    from backend.modules.module4_face.stub import run_face_verification

    result = run_face_verification(b"fake_doc_bytes", b"fake_selfie_bytes")
    assert result["module"] == "face_verification"
    assert result["status"] in ("match", "mismatch", "no_face_detected")


def test_similarity_in_valid_range_when_present():
    from backend.modules.module4_face.stub import run_face_verification

    result = run_face_verification(b"fake_doc_bytes", b"fake_selfie_bytes")
    if result["status"] != "no_face_detected":
        assert result["similarity"] is not None
        assert 0.0 <= result["similarity"] <= 1.0


def test_face_detection_flags_are_booleans():
    from backend.modules.module4_face.stub import run_face_verification

    result = run_face_verification(b"fake_doc_bytes", b"fake_selfie_bytes")
    assert isinstance(result["face_detected_in_document"], bool)
    assert isinstance(result["face_detected_in_live"], bool)


@pytest.mark.skip(reason="No real face fixtures available yet, waiting on teammate selfies. Un-skip once fixtures exist.")
def test_matched_pair_returns_match():
    pass


@pytest.mark.skip(reason="No real face fixtures available yet, waiting on teammate selfies. Un-skip once fixtures exist.")
def test_mismatched_pair_returns_mismatch():
    pass


# TODO: once face_verification.py is implemented AND face fixtures exist:
# - un-skip and implement the two tests above using real fixture files
# - test_no_face_in_image_returns_no_face_detected_not_exception()
# - test_similarity_is_null_when_no_face_detected()