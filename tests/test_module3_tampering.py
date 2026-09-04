"""
Unit tests for Module 3 - Tampering Detection.
Real tests should run against data/fixtures/clean/ (expect overall_tamper_flag=False)
and data/fixtures/tampered/ (expect overall_tamper_flag=True).
"""
import csv
import os
import pytest

MANIFEST_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "fixtures", "fixtures_manifest.csv"
)


def test_stub_returns_expected_schema():
    from backend.modules.module3_tampering.stub import run_tampering_detection

    result = run_tampering_detection(b"fake_bytes")
    assert result["module"] == "tampering_detection"
    assert 0.0 <= result["ela_score"] <= 1.0
    assert 0.0 <= result["ela_clarity"] <= 1.0
    assert isinstance(result["overall_tamper_flag"], bool)


@pytest.mark.skip(reason="Requires real ela.py/copy_move.py logic -- stub always "
                         "returns overall_tamper_flag=False regardless of input, "
                         "so this test is meaningless until Module 3's real "
                         "implementation replaces the stub. Un-skip once that lands.")
def test_clean_fixtures_not_flagged():
    """Every fixture marked category=clean in the manifest should NOT be flagged."""
    from backend.modules.module3_tampering.stub import run_tampering_detection

    with open(MANIFEST_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        if row["category"] != "clean":
            continue
        img_path = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures",
                                 "clean", row["filename"])
        with open(img_path, "rb") as img_f:
            result = run_tampering_detection(img_f.read())
        assert result["overall_tamper_flag"] is False, \
            f"{row['filename']} is clean but was flagged as tampered"


@pytest.mark.skip(reason="Requires real ela.py/copy_move.py logic -- see note above.")
def test_tampered_fixtures_are_flagged():
    """Every fixture marked category=tampered AND expected_module3_result=true
    in the manifest should be flagged."""
    from backend.modules.module3_tampering.stub import run_tampering_detection

    with open(MANIFEST_PATH, newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        if row["category"] != "tampered" or row["expected_module3_result"] != "true":
            continue
        img_path = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures",
                                 "tampered", row["filename"])
        with open(img_path, "rb") as img_f:
            result = run_tampering_detection(img_f.read())
        assert result["overall_tamper_flag"] is True, \
            f"{row['filename']} is tampered but was NOT flagged"


# TODO: once ela.py / copy_move.py / exif_check.py are implemented:
# - un-skip the two tests above
# - test_low_clarity_on_recompressed_image()  -- degraded image should lower ela_clarity, not silently pass