
"""
Full pipeline wiring. All six modules now point at their real
implementations instead of stub.py, per the Day 3+ convention this file's
original docstring described — function signatures and the schema
contract (schema/module_io_schema.json) were preserved, not changed,
except where explicitly flagged below.
"""
from fastapi import APIRouter, UploadFile, File, Form

from backend.modules.module1_ocr.ocr_extraction import run_ocr
from backend.modules.module2_validation.document_validation import run_validation
from backend.modules.module3_tampering.tampering_detection import run_tampering_detection
from backend.modules.module4_face.face_verification import run_face_verification
from backend.modules.module5_authority_match.authority_match import run_authority_match
from backend.modules.module6_blockchain.blockchain_ledger import write_ledger_record
from backend.modules.module6_blockchain.identity_reuse import search_for_identity_reuse
from backend.database.ledger_store import get_all_records
from backend.risk_engine.scoring import compute_risk_score

router = APIRouter()


@router.post("/screen")
async def screen_document(
    doc_image: UploadFile = File(...),
    live_selfie: UploadFile = File(...),
    doc_type: str = Form(...),
):
    """
    Full pipeline: upload -> OCR -> validation -> tampering -> face ->
    authority match -> risk scoring -> blockchain ledger -> response.
    """
    doc_bytes = await doc_image.read()
    selfie_bytes = await live_selfie.read()

    ocr_result = run_ocr(doc_bytes, doc_type)
    validation_result = run_validation(ocr_result, doc_type)
    tamper_result = run_tampering_detection(doc_bytes)
    face_result = run_face_verification(doc_bytes, selfie_bytes)

    # Signature fix: run_authority_match needs the document IMAGE (to
    # extract a face embedding), which ocr_result alone does not carry.
    # See backend/modules/module5_authority_match/authority_match.py's
    # docstring for the full explanation of why this differs from
    # stub.py's original one-argument signature.
    authority_result = run_authority_match(ocr_result, doc_bytes)

    # Identity-reuse check must run BEFORE risk scoring, not after — the
    # flag needs to be known in time to influence risk_score/risk_band,
    # not just recorded afterward. Previously this only ran inside
    # write_ledger_record(), by which point compute_risk_score() had
    # already returned its answer blind to it.
    declared_identity = ocr_result.get("extracted_fields", {}).get("name", {}).get("value")
    declared_doc_number = ocr_result.get("extracted_fields", {}).get("passport_number", {}).get("value")
    doc_embedding = face_result.get("doc_embedding")
    identity_reuse_result = search_for_identity_reuse(doc_embedding, declared_identity, declared_doc_number)

    risk_result = compute_risk_score(
        validation_result, tamper_result, face_result, authority_result,
        identity_reuse_flag=identity_reuse_result["identity_reuse_flag"],
    )

    ledger_record = write_ledger_record(
        ocr_result, validation_result, tamper_result, face_result, risk_result,
        authority_result, identity_reuse_result,
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
    return {"records": get_all_records()}