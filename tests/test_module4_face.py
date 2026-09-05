"""
Unit tests for Module 4 - Face Verification.
Real tests run against data/fixtures/faces/matched/ (expect status="match")
and data/fixtures/faces/mismatched/ (expect status="mismatch"), using the
pairs listed in data/fixtures/faces/face_pairs_manifest.json.
"""
import json
import os
import pytest

FACE_PAIRS_MANIFEST = os.path.join(
    os.path.dirname(__file__), "..", "data", "fixtures", "faces", "face_pairs_manifest.json"
)
FACES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures", "faces")


def load_face_pairs():
    with open(FACE_PAIRS_MANIFEST) as f:
        return json.load(f)


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


def test_face_pairs_manifest_files_all_exist_on_disk():
    """Sanity check: every file the manifest references must actually exist."""
    pairs = load_face_pairs()
    assert len(pairs) > 0, "No face pairs found in manifest"
    for pair in pairs:
        doc_path = os.path.join(FACES_DIR, pair["document_file"])
        selfie_path = os.path.join(FACES_DIR, pair["selfie_file"])
        assert os.path.isfile(doc_path), f"Missing document file: {doc_path}"
        assert os.path.isfile(selfie_path), f"Missing selfie file: {selfie_path}"


@pytest.mark.skip(reason="Stub always returns status=match regardless of input -- meaningless until real face_verification.py exists. Un-skip once that lands.")
def test_matched_pairs_return_match():
    from backend.modules.module4_face.stub import run_face_verification

    pairs = [p for p in load_face_pairs() if p["category"] == "matched"]
    for pair in pairs:
        doc_path = os.path.join(FACES_DIR, pair["document_file"])
        selfie_path = os.path.join(FACES_DIR, pair["selfie_file"])
        with open(doc_path, "rb") as f:
            doc_bytes = f.read()
        with open(selfie_path, "rb") as f:
            selfie_bytes = f.read()
        result = run_face_verification(doc_bytes, selfie_bytes)
        assert result["status"] == "match", \
            f"{pair['document_identity']}'s own selfie should match, got {result['status']}"


@pytest.mark.skip(reason="Stub always returns status=match regardless of input -- meaningless until real face_verification.py exists. Un-skip once that lands.")
def test_mismatched_pairs_return_mismatch():
    from backend.modules.module4_face.stub import run_face_verification

    pairs = [p for p in load_face_pairs() if p["category"] == "mismatched"]
    for pair in pairs:
        doc_path = os.path.join(FACES_DIR, pair["document_file"])
        selfie_path = os.path.join(FACES_DIR, pair["selfie_file"])
        with open(doc_path, "rb") as f:
            doc_bytes = f.read()
        with open(selfie_path, "rb") as f:
            selfie_bytes = f.read()
        result = run_face_verification(doc_bytes, selfie_bytes)
        assert result["status"] == "mismatch", \
            f"{pair['document_identity']} vs {pair['selfie_identity']} should mismatch, got {result['status']}"