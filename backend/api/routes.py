"""
FastAPI routes for the document-screening pipeline.

Data sources used by the dashboard:

DB #1
    backend.database.mock_db1_issuance
    Issuance / blacklist lookup

DB #2
    backend.database.mock_db2_authority_ref
    Independent authority-reference photo lookup

DB #3
    data/ledger/audit_ledger.json
    Screening audit / blockchain ledger
"""

import os

from fastapi import APIRouter, UploadFile, File, Form, Query

from backend.modules.module1_ocr.ocr_extraction import run_ocr
from backend.modules.module2_validation.document_validation import run_validation
from backend.modules.module3_tampering.tampering_detection import (
    run_tampering_detection,
)
from backend.modules.module4_face.face_verification import (
    run_face_verification,
)
from backend.modules.module5_authority_match.authority_match import (
    run_authority_match,
)
from backend.modules.module6_blockchain.blockchain_ledger import (
    write_ledger_record,
)
from backend.modules.module6_blockchain.identity_reuse import (
    search_for_identity_reuse,
)
from backend.database.ledger_store import get_all_records
from backend.database.mock_db1_issuance import (
    ISSUANCE_TABLE,
    lookup_document_status,
)
from backend.database.mock_db2_authority_ref import (
    get_reference_photo_path,
)
from backend.risk_engine.scoring import compute_risk_score


router = APIRouter()


# =========================================================
# MAIN SCREENING PIPELINE
# =========================================================

@router.post("/screen")
async def screen_document(
    doc_image: UploadFile = File(...),
    live_selfie: UploadFile = File(...),
    doc_type: str = Form(...),
):
    """
    Full pipeline:

    OCR
        ->
    Validation
        ->
    Tampering
        ->
    Face
        ->
    Authority reference
        ->
    Identity reuse
        ->
    Risk
        ->
    Blockchain ledger
    """

    doc_bytes = await doc_image.read()
    selfie_bytes = await live_selfie.read()

    # -----------------------------------------------------
    # MODULE 1 - OCR
    # -----------------------------------------------------

    ocr_result = run_ocr(
        doc_bytes,
        doc_type,
    )

    # -----------------------------------------------------
    # MODULE 2 - VALIDATION
    # -----------------------------------------------------

    validation_result = run_validation(
        ocr_result,
        doc_type,
    )

    # -----------------------------------------------------
    # MODULE 3 - TAMPERING
    # -----------------------------------------------------

    tamper_result = run_tampering_detection(
        doc_bytes,
    )

    # -----------------------------------------------------
    # MODULE 4 - FACE
    # -----------------------------------------------------

    face_result = run_face_verification(
        doc_bytes,
        selfie_bytes,
    )

    # -----------------------------------------------------
    # MODULE 5 - AUTHORITY REFERENCE
    # -----------------------------------------------------

    authority_result = run_authority_match(
        ocr_result,
        doc_bytes,
    )

    # -----------------------------------------------------
    # EXTRACT DOCUMENT IDENTITY
    # -----------------------------------------------------

    extracted_fields = (
        ocr_result.get("extracted_fields", {})
    )

    declared_identity = (
        extracted_fields
        .get("name", {})
        .get("value")
    )

    declared_doc_number = (
        extracted_fields
        .get("passport_number", {})
        .get("value")
    )

    # -----------------------------------------------------
    # MODULE 6A - IDENTITY REUSE
    # -----------------------------------------------------

    doc_embedding = face_result.get(
        "doc_embedding"
    )

    identity_reuse_result = (
        search_for_identity_reuse(
            doc_embedding,
            declared_identity,
            declared_doc_number,
        )
    )

    # -----------------------------------------------------
    # RISK ENGINE
    # -----------------------------------------------------

    risk_result = compute_risk_score(
        validation_result,
        tamper_result,
        face_result,
        authority_result,
        identity_reuse_flag=(
            identity_reuse_result[
                "identity_reuse_flag"
            ]
        ),
    )

    # -----------------------------------------------------
    # MODULE 6B - BLOCKCHAIN LEDGER
    # -----------------------------------------------------

    ledger_record = write_ledger_record(
        ocr_result,
        validation_result,
        tamper_result,
        face_result,
        risk_result,
        authority_result,
        identity_reuse_result,
    )

    # -----------------------------------------------------
    # FINAL RESPONSE
    # -----------------------------------------------------

    return {
        "ocr": ocr_result,
        "validation": validation_result,
        "tampering": tamper_result,
        "face": face_result,
        "authority_match": authority_result,
        "risk": risk_result,
        "ledger": ledger_record,
    }


# =========================================================
# DB #3 - FULL BLOCKCHAIN LEDGER
# =========================================================

@router.get("/ledger")
def get_ledger():
    """
    Return all persisted screening records.

    The underlying ledger_store currently uses:
        hash
        prev_hash

    The frontend is designed to support these fields directly.
    """

    records = get_all_records()

    return {
        "records": records,
        "count": len(records),
    }


# =========================================================
# DB #3 - LEDGER SEARCH
# =========================================================

@router.get("/ledger/search")
def search_ledger(
    document_number: str | None = Query(
        default=None
    ),
    record_hash: str | None = Query(
        default=None
    ),
    identity: str | None = Query(
        default=None
    ),
):
    """
    Search the blockchain audit ledger.

    Supported search keys:

        document_number
        record_hash
        identity

    Multiple historical screenings can exist for
    the same document number, therefore ledger search
    always returns a list of records.
    """

    records = get_all_records()

    if not document_number and not record_hash and not identity:
        return {
            "found": False,
            "search_type": None,
            "records": [],
            "message": (
                "Provide document_number, "
                "record_hash or identity."
            ),
        }

    matches = []

    # -----------------------------------------------------
    # DOCUMENT NUMBER
    # -----------------------------------------------------

    if document_number:

        query = document_number.strip().upper()

        for record in records:

            stored_number = str(
                record.get(
                    "declared_doc_number",
                    "",
                )
                or ""
            ).strip().upper()

            if stored_number == query:
                matches.append(record)

        return {
            "found": len(matches) > 0,
            "search_type": "document_number",
            "query": document_number,
            "records": matches,
        }

    # -----------------------------------------------------
    # RECORD HASH
    # -----------------------------------------------------

    if record_hash:

        query = record_hash.strip()

        for record in records:

            stored_hash = (
                record.get("record_hash")
                or record.get("hash")
            )

            if stored_hash == query:
                matches.append(record)

        return {
            "found": len(matches) > 0,
            "search_type": "record_hash",
            "query": record_hash,
            "records": matches,
        }

    # -----------------------------------------------------
    # IDENTITY
    # -----------------------------------------------------

    query = identity.strip().upper()

    for record in records:

        stored_identity = str(
            record.get(
                "declared_identity",
                "",
            )
            or ""
        ).strip().upper()

        if stored_identity == query:
            matches.append(record)

    return {
        "found": len(matches) > 0,
        "search_type": "identity",
        "query": identity,
        "records": matches,
    }


# =========================================================
# DB #1 - ISSUANCE / BLACKLIST
# =========================================================

@router.get("/issuance/search")
def search_issuance(
    document_number: str = Query(...),
):
    """
    Search Mock DB #1.

    This is the issuance / blacklist database.

    It answers:

        clear
        blacklisted
        expired
        not_found
    """

    normalized_number = (
        document_number.strip().upper()
    )

    status = lookup_document_status(
        normalized_number
    )

    entry = ISSUANCE_TABLE.get(
        normalized_number
    )

    return {
        "source": "mock_db_1",
        "source_name": (
            "Mock DB #1 - Issuance / Blacklist"
        ),
        "found": entry is not None,
        "document_number": normalized_number,
        "status": status,
        "issued_to": (
            entry.get("issued_to")
            if entry
            else None
        ),
    }


# =========================================================
# DB #2 - AUTHORITY REFERENCE
# =========================================================

@router.get("/authority/search")
def search_authority(
    document_number: str = Query(...),
):
    """
    Search Mock DB #2.

    This database contains the independently trusted
    reference photo associated with a document number.

    It is NOT the same thing as the issuance database
    and NOT the same thing as the blockchain ledger.
    """

    normalized_number = (
        document_number.strip().upper()
    )

    reference_path = get_reference_photo_path(
        normalized_number
    )

    # Project root:
    # backend/api/routes.py
    #   -> backend/api
    #   -> backend
    #   -> project root
    project_root = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
        )
    )

    reference_exists = False

    if reference_path:

        absolute_reference_path = os.path.join(
            project_root,
            reference_path,
        )

        reference_exists = os.path.exists(
            absolute_reference_path
        )

    return {
        "source": "mock_db_2",
        "source_name": (
            "Mock DB #2 - Authority Reference"
        ),
        "found": reference_path is not None,
        "document_number": normalized_number,
        "reference_available": reference_exists,
        "reference_source": "mock_db_2",
        "reference_file": (
            os.path.basename(reference_path)
            if reference_path
            else None
        ),
    }