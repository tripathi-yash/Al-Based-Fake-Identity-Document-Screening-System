"""
Integration test: runs the full pipeline against every fixture listed in
data/fixtures/fixtures_manifest.csv and checks actual results against the
expected results recorded there. This is your automated proof that the
whole system behaves as claimed in the demo script.

Run this on Day 8 (per action_plan.pdf Section 9, "Testing" day) after all
modules have their real implementations in place.
"""
import csv
import os

MANIFEST_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "fixtures", "fixtures_manifest.csv"
)
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures")

VALID_CATEGORIES = {"clean", "tampered", "authority_ref"}
VALID_MODULE3_RESULTS = {"true", "false"}
VALID_MODULE4_RESULTS = {"match", "mismatch", "no_face_detected"}


def load_manifest():
    with open(MANIFEST_PATH, newline="") as f:
        return list(csv.DictReader(f))


def test_manifest_file_exists_and_has_entries():
    rows = load_manifest()
    assert rows is not None
    assert len(rows) > 0, "Manifest has no fixture rows yet"


def test_every_manifest_row_has_all_required_columns():
    rows = load_manifest()
    required_columns = {"filename", "doc_type", "category",
                         "expected_module3_result", "expected_module4_result",
                         "linked_db_id", "notes"}
    for row in rows:
        missing = required_columns - set(row.keys())
        assert not missing, f"Row for {row.get('filename')} missing columns: {missing}"


def test_every_manifest_filename_actually_exists_on_disk():
    """Catches the classic mistake: a manifest row exists but the image
    file was never saved, or the filename has a typo."""
    rows = load_manifest()
    for row in rows:
        expected_path = os.path.join(FIXTURES_DIR, row["category"], row["filename"])
        assert os.path.isfile(expected_path), \
            f"Manifest references '{row['filename']}' but no file found at {expected_path}"


def test_category_values_are_valid():
    rows = load_manifest()
    for row in rows:
        assert row["category"] in VALID_CATEGORIES, \
            f"{row['filename']}: invalid category '{row['category']}'"


def test_expected_module3_result_is_valid():
    rows = load_manifest()
    for row in rows:
        assert row["expected_module3_result"] in VALID_MODULE3_RESULTS, \
            f"{row['filename']}: invalid expected_module3_result '{row['expected_module3_result']}' (must be true/false)"


def test_expected_module4_result_is_valid():
    rows = load_manifest()
    for row in rows:
        assert row["expected_module4_result"] in VALID_MODULE4_RESULTS, \
            f"{row['filename']}: invalid expected_module4_result '{row['expected_module4_result']}'"


# TODO: for each row in load_manifest(), run the full /screen pipeline
# against `filename` and assert:
#   - tampering result matches expected_module3_result
#   - face result matches expected_module4_result
# This turns your fixtures manifest into a real regression test suite.
# (Blocked until main.py's real /screen endpoint exists - currently only
# individual module stubs exist, not a wired-together pipeline.)