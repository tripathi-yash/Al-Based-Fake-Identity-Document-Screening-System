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


def load_manifest():
    with open(MANIFEST_PATH, newline="") as f:
        return list(csv.DictReader(f))


def test_manifest_file_exists_and_has_entries():
    rows = load_manifest()
    # TODO: once fixtures are built (action_plan.pdf Section 8), this should
    # assert len(rows) >= 25 or similar, not just that the file is readable
    assert rows is not None


# TODO: for each row in load_manifest(), run the full /screen pipeline
# against `filename` and assert:
#   - tampering result matches expected_module3_result
#   - face result matches expected_module4_result
# This turns your fixtures manifest into a real regression test suite.
