"""
Unit tests for Module 4 - Face Verification.

HONESTY NOTE: face_verification.py's source was not available when
writing this file, so these are SCHEMA-CONTRACT tests derived from
module_io_schema.json, plus real match/mismatch tests using your 5
teammates' actual document+selfie fixtures (skipped automatically if
files aren't found at the paths below — adjust TEAM_DIR to match).
"""
import os
import pytest

from backend.modules.module4_face.face_verification import run_face_verification

TEAM_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures", "faces", "matched")

ASHRAY_DOC = os.path.join(TEAM_DIR, "ashray_document.jpg")
ASHRAY_SELFIE = os.path.join(TEAM_DIR, "ashray_selfie.jpg")
RIYA_DOC = os.path.join(TEAM_DIR, "riya_document.jpg")
RIYA_SELFIE = os.path.join(TEAM_DIR, "riya_selfie.jpg")


def _skip_if_missing(*paths):
    missing = [p for p in paths if not os.path.isfile(p)]
    return pytest.mark.skipif(bool(missing), reason=f"Fixture(s) not found: {missing}")


def _read(path):
    with open(path, "rb") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------
def test_garbage_bytes_never_raises():
    result = run_face_verification(b"not an image", b"also not an image")
    assert result["status"] in ("match", "mismatch", "no_face_detected")


def test_output_has_required_schema_keys():
    result = run_face_verification(b"garbage", b"garbage")
    for key in ("module", "status", "threshold_used",
                "face_detected_in_document", "face_detected_in_live"):
        assert key in result
    assert isinstance(result["face_detected_in_document"], bool)
    assert isinstance(result["face_detected_in_live"], bool)
    if result["similarity"] is not None:
        assert 0.0 <= result["similarity"] <= 1.0


def test_no_face_in_garbage_bytes():
    """Garbage bytes should decode to no detectable face, not a false match."""
    result = run_face_verification(b"not an image", b"also not an image")
    assert result["status"] == "no_face_detected"


# ---------------------------------------------------------------------------
# Real fixture tests
# ---------------------------------------------------------------------------
@_skip_if_missing(ASHRAY_DOC, ASHRAY_SELFIE)
def test_own_document_and_selfie_match():
    result = run_face_verification(_read(ASHRAY_DOC), _read(ASHRAY_SELFIE))
    assert result["status"] == "match", \
        f"Expected match for Ashray's own doc+selfie, got {result['status']} (similarity={result['similarity']})"


@_skip_if_missing(ASHRAY_DOC, RIYA_SELFIE)
def test_cross_pair_mismatches():
    result = run_face_verification(_read(ASHRAY_DOC), _read(RIYA_SELFIE))
    assert result["status"] == "mismatch", \
        f"Expected mismatch for Ashray doc + Riya selfie, got {result['status']} (similarity={result['similarity']})"


@_skip_if_missing(ASHRAY_DOC, ASHRAY_SELFIE)
def test_doc_embedding_present_for_module6_consumption():
    """Additive field per schema — Module 6b depends on this being populated."""
    result = run_face_verification(_read(ASHRAY_DOC), _read(ASHRAY_SELFIE))
    assert "doc_embedding" in result
    if result["face_detected_in_document"]:
        assert result["doc_embedding"] is not None
        assert isinstance(result["doc_embedding"], list)