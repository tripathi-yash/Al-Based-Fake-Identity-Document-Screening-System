"""
Day 2-3 goal: wire every module's stub together here so the full pipeline
runs end-to-end with mock data before any real algorithm is finished.
See docs/action_plan.pdf Section 9a.

From Day 3 onward, swap each `from modules.moduleX_xxx.stub import run` line
for `from modules.moduleX_xxx.<real_file> import run` - the function
signature and return schema (schema/module_io_schema.json) must not change.
"""
from fastapi import APIRouter, UploadFile, File, Form

from modules.module1_ocr.stub import run_ocr
from modules.module2_validation.stub import run_validation
from modules.module3_tampering.stub import run_tampering_detection
from modules.module4_face.stub import run_face_verification
from modules.module5_authority_match.stub import run_authority_match
from modules.module6_blockchain.stub import write_ledger_record
from risk_engine.scoring import compute_risk_score  # implement alongside stubs, see risk_engine/scoring.py

router = APIRouter()


@router.post("/screen")
async def screen_document(
    doc_image: UploadFile = File(...),
    live_selfie: UploadFile = File(...),
    doc_type: str = Form(...),
):
    """
    Full pipeline: upload -> OCR -> validation -> tampering -> face ->
    (authority match) -> risk scoring -> blockchain ledger -> response.
    """
    doc_bytes = await doc_image.read()
    selfie_bytes = await live_selfie.read()

    ocr_result = run_ocr(doc_bytes, doc_type)
    validation_result = run_validation(ocr_result, doc_type)
    tamper_result = run_tampering_detection(doc_bytes)
    face_result = run_face_verification(doc_bytes, selfie_bytes)
    authority_result = run_authority_match(ocr_result)

    risk_result = compute_risk_score(
        validation_result, tamper_result, face_result, authority_result
    )

    ledger_record = write_ledger_record(
        ocr_result, validation_result, tamper_result, face_result, risk_result
    )

    return {
        "ocr": ocr_result,
        "validation": validation_result,
        "tampering": tamper_result,
        "face": face_result,
        "authority_match": authority_result,
        "risk": risk_result,
        "ledger": ledger_record,
    }


@router.get("/ledger")
def get_ledger():
    """Return the full blockchain ledger for the dashboard's audit trail view."""
    # TODO: read from backend/database/ledger_store.py
    return {"records": []}
