"""
Mock DB #1 - issuance/blacklist lookup table.
Simulates a government passport/visa issuance database. Explicitly a mock -
state this plainly in the pitch (action_plan.pdf Section 7).
Owner: fill in during Day 3-4 (backend/data-comfortable teammate).
IDs used here MUST exactly match IDs used in data/fixtures - see
data/fixtures/fixtures_manifest.csv as the cross-reference.
"""

# TODO: populate with entries drawn from your MIDV-500 fixture subset
ISSUANCE_TABLE = {
    # "P1234567": {"status": "clear", "issued_to": "JOHN DOE"},
    # "P7654321": {"status": "blacklisted", "issued_to": "JANE SMITH"},
    # "P1112223": {"status": "expired", "issued_to": "ALEX KIM"},
}


def lookup_document_status(document_number: str) -> str:
    entry = ISSUANCE_TABLE.get(document_number)
    if entry is None:
        return "not_found"
    return entry["status"]
