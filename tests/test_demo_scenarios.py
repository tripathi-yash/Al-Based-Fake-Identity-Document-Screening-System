"""
tests/test_demo_scenarios.py

End-to-end scenario tests for the /screen pipeline — this is Section 3
of the checklist ("6 demo scenarios"), NOT the per-module unit tests
(test_module1_ocr.py etc., which are Case A / isolated tests).

Run with:
    pytest tests/test_demo_scenarios.py -v -s
    (the -s flag lets the printed JSON summaries show up in your terminal)

FIX BEFORE RUNNING:
    The import below assumes your FastAPI() instance is created in a
    file importable as `main` (e.g. backend/main.py with `app = FastAPI()`
    and `app.include_router(router)` inside it). Update the import path
    to match your actual project layout if this fails.
"""
import pytest
import os
from fastapi.testclient import TestClient

from backend.main import app  # <-- FIX THIS IMPORT PATH if it doesn't match your project

client = TestClient(app)

# ---------------------------------------------------------------------------
# Update these paths to wherever your fixtures actually live on disk.
# ---------------------------------------------------------------------------
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures")

FIXTURES = FIXTURES_DIR
CLEAN_PASSPORT = f"{FIXTURES}/clean/clean_passport_01.jpg"
TAMPERED_DOB = f"{FIXTURES}/tampered/tampered_02_dob_alter.jpg"
TAMPERED_STAMP = f"{FIXTURES}/tampered/tampered_03_stamp_clone.jpg"

TEAM = f"{FIXTURES}/faces/matched"
ASHRAY_DOC = f"{TEAM}/ashray_document.jpg"
ASHRAY_SELFIE = f"{TEAM}/ashray_selfie.jpg"
RIYA_DOC = f"{TEAM}/riya_document.jpg"
RIYA_SELFIE = f"{TEAM}/riya_selfie.jpg"
ASHRAY_ID_REUSE = f"{FIXTURES}/id_reuse/ashray's_id_reuse.jpg"

ASHRAY_PASSPORT_NO = "N1234567"  # must match mock_db1_issuance.py / mock_db2_authority_ref.py
FABRICATED_PASSPORT_NO = "F9999999"  # deliberately NOT in either mock DB


def _screen(doc_path: str, selfie_path: str, doc_type: str = "passport"):
    """Shared helper: POST to /screen exactly like a real client would."""
    with open(doc_path, "rb") as doc, open(selfie_path, "rb") as selfie:
        response = client.post(
            "/screen",
            files={
                "doc_image": ("doc.jpg", doc, "image/jpeg"),
                "live_selfie": ("selfie.jpg", selfie, "image/jpeg"),
            },
            data={"doc_type": doc_type},
        )
    return response


def _print_summary(label: str, response):
    print(f"\n{'=' * 70}\nSCENARIO: {label}\n{'=' * 70}")
    print(f"HTTP status: {response.status_code}")
    body = response.json()
    risk = body.get("risk", {})
    print(f"risk_band:            {risk.get('risk_band')}")
    print(f"final_recommendation: {risk.get('final_recommendation')}")
    print(f"evidence_strength:    {risk.get('evidence_strength')}")
    print(f"contributing_flags:   {risk.get('contributing_flags')}")
    print(f"validation flags:     {body.get('validation', {}).get('flags')}")
    print(f"tamper_verdict:       {body.get('tampering', {}).get('tamper_verdict')}")
    print(f"face status:          {body.get('face', {}).get('status')}")
    print(f"authority status:     {body.get('authority_match', {}).get('status')}")
    print(f"identity_reuse_flag:  {body.get('ledger', {}).get('identity_reuse_flag')}")
    return body



# ---------------------------------------------------------------------------
# Scenario 6 — Identity reuse across two screenings
# ---------------------------------------------------------------------------
def test_scenario_6_identity_reuse():
    # First screening: Ashray, real passport number -> establishes a
    # ledger record with his face embedding under his real identity.
    first = _screen(ASHRAY_DOC, ASHRAY_SELFIE, doc_type="passport")
    _print_summary("6a. First screening (Ashray, real ID)", first)
    assert first.json()["ledger"]["identity_reuse_flag"] is False

    # Second screening: SAME face, but declared under a fabricated
    # passport number that exists in neither mock_db1 nor mock_db2.
    # NOTE: since run_ocr() reads the declared number directly off the
    # document image (per ocr_extraction.py), you cannot just "pass a
    # different number" via the API — you need a second document image
    # fixture with the same face but a different printed/MRZ passport
    # number. Flag this to your team as a fixture gap if one doesn't
    # exist yet.
    second = _screen(ASHRAY_ID_REUSE, ASHRAY_SELFIE, doc_type="passport")
    body = _print_summary("6b. Second screening (same face, should differ in declared ID)", second)
    print("NOTE: this will NOT show reuse=True until a fixture exists where "
          "Ashray's face is paired with a different declared passport number.")