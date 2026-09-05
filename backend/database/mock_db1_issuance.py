"""
Mock DB #1 - issuance/blacklist lookup table.
Simulates a government passport/visa issuance database. Explicitly a mock -
state this plainly in the pitch (action_plan.pdf Section 7).
IDs used here MUST exactly match IDs used in data/fixtures - see
data/fixtures/fixtures_manifest.csv as the cross-reference.

This is the SINGLE canonical issuance table for the whole project.
document_validation.py previously embedded its own separate copy of this
table with a different shape ({"P1234567": "issued"} instead of
{"P1234567": {"status": "clear", ...}}) — that duplicate has been removed;
document_validation.py now imports lookup_document_status() from here.

P1234567 is deliberately kept consistent with
backend/database/mock_db2_authority_ref.py's AUTHORITY_REFERENCE_TABLE,
which uses the same ID — this lets a single test fixture exercise Module 2,
Module 5, and Module 6 consistently without cross-module ID mismatches.
"""

ISSUANCE_TABLE = {
    "P1234567": {"status": "clear", "issued_to": "JOHN DOE"},
    "P7654321": {"status": "blacklisted", "issued_to": "JANE SMITH"},
    "P1112223": {"status": "expired", "issued_to": "ALEX KIM"},
    "P9988776": {"status": "clear", "issued_to": "PRIYA SHARMA"},
    "V5566778": {"status": "clear", "issued_to": "SAM CHEN"},
    "V2233445": {"status": "blacklisted", "issued_to": "RYAN COLE"},
    "N4455667": {"status": "clear", "issued_to": "MEERA IYER"},
    "N7788990": {"status": "expired", "issued_to": "DAVID OKORO"},
}


def lookup_document_status(document_number: str) -> str:
    """Returns 'clear' | 'blacklisted' | 'expired' | 'not_found'."""
    if not document_number:
        return "not_found"
    entry = ISSUANCE_TABLE.get(document_number.strip().upper())
    if entry is None:
        return "not_found"
    return entry["status"]