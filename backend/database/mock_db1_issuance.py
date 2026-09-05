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
    "N1234567": {"status": "clear", "issued_to": "ASHRAY KUMAR SHARMA"},
    "N2345678": {"status": "blacklisted", "issued_to": "PRIYA VERMA"},
    "N3456789": {"status": "expired", "issued_to": "AAMIR RAZA KHAN"},
    "N4567890": {"status": "clear", "issued_to": "LAKSHMI IYER"},
    "N5678901": {"status": "clear", "issued_to": "ARJUN SINGH"},
}

def lookup_document_status(document_number: str) -> str:
    """Returns 'clear' | 'blacklisted' | 'expired' | 'not_found'."""
    if not document_number:
        return "not_found"

    entry = ISSUANCE_TABLE.get(document_number.strip().upper())

    if entry is None:
        return "not_found"

    return entry["status"]