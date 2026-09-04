"""
Real implementation for Module 6 - Blockchain Ledger. Combines
hash_chain.py (6a - ledger integrity) + identity_reuse.py (6b - embedding
similarity search) into a single write_ledger_record() call, same
function signature/schema as stub.py.

This file did not exist yet in the Day-2 scaffold (only stub.py,
hash_chain.py, and identity_reuse.py did) — it's the missing combiner
that routes.py should import from once Module 6 is real:
    from modules.module6_blockchain.blockchain_ledger import write_ledger_record
(replacing the current `from modules.module6_blockchain.stub import ...`)
"""
from datetime import datetime, timezone

from .hash_chain import compute_record_hash
from .identity_reuse import search_for_identity_reuse
from ...database.ledger_store import append_record, get_latest_hash


def write_ledger_record(
    ocr_result, validation_result, tamper_result, face_result, risk_result, authority_result=None
) -> dict:
    """
    Returns schema matches schema/module_io_schema.json ->
    module6_blockchain_ledger exactly, plus an additional
    authority_match_status field (see note below).

    face_embedding is pulled from face_result's doc_embedding field
    (added to Module 4's return dict) — required for
    identity_reuse_detection to have anything to compare against for
    THIS screening.

    authority_result is OPTIONAL (defaults to None) so this stays
    backward compatible with callers that don't yet pass Module 5's
    output (e.g. before routes.py is updated, or when Module 5 is
    skipped entirely as a stretch goal per the action plan). When
    provided, its status/similarity are preserved in the permanent
    record — this matters because a Module 5 "mismatch" is the ONE
    signal that catches a flawless physical forgery; that verdict must
    be part of the tamper-evident audit trail, not just printed to a
    console and discarded.
    """
    declared_identity = ocr_result.get("extracted_fields", {}).get("name", {}).get("value")
    declared_doc_number = ocr_result.get("extracted_fields", {}).get("passport_number", {}).get("value")

    new_embedding = face_result.get("doc_embedding")

    reuse_result = search_for_identity_reuse(new_embedding, declared_identity, declared_doc_number)

    authority_match_status = authority_result.get("status") if authority_result else None
    authority_match_similarity = authority_result.get("similarity") if authority_result else None

    previous_hash = get_latest_hash()
    record_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "declared_identity": declared_identity,
        "declared_doc_number": declared_doc_number,
        "risk_result": risk_result,
        "face_embedding": new_embedding,
        "authority_match_status": authority_match_status,
        "authority_match_similarity": authority_match_similarity,
    }
    record_hash = compute_record_hash(previous_hash, record_data)

    stored_record = append_record({**record_data, "prev_hash": previous_hash, "hash": record_hash})

    return {
        "module": "blockchain_ledger",
        "status": "success",
        "record_hash": record_hash,
        "previous_hash": previous_hash,
        "timestamp": stored_record["timestamp"],
        "identity_reuse_flag": reuse_result["identity_reuse_flag"],
        "identity_reuse_matches": reuse_result["identity_reuse_matches"],
        "authority_match_status": authority_match_status,
    }


if __name__ == "__main__":
    import os
    from ..module1_ocr.stub import run_ocr
    from ..module2_validation.stub import run_validation
    from ..module3_tampering.tampering_detection import run_tampering_detection
    from ..module4_face.face_verification import run_face_verification
    from ..module5_authority_match.authority_match import run_authority_match
    from ...risk_engine.scoring import compute_risk_score

    doc_type = None
    IMAGE_PATH = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "data", "fixtures", "clean", "student_id.jpg"
    )

    with open(IMAGE_PATH, "rb") as file:
        image_bytes = file.read()
    live_selfie_bytes = image_bytes  # reusing the same college-ID image to stand in for a selfie

    ocr_result = run_ocr(doc_type, doc_type)
    validation_result = run_validation(ocr_result, doc_type)
    tamper_result = run_tampering_detection(image_bytes)  # single arg, not two

    # Module 4: doc photo vs "live selfie" (same image here, for smoke testing only)
    face_result = run_face_verification(image_bytes, live_selfie_bytes)

    # Module 5: doc photo vs authority mock DB record — separate call,
    # was imported but never actually invoked before
    fake_ocr_result = {"extracted_fields": {"passport_number": {"value": "P1234567"}}}
    authority_result = run_authority_match(fake_ocr_result, image_bytes)

    # NOTE: verify compute_risk_score's actual declared signature in
    # scoring.py before running this — it may not yet accept
    # authority_result as a parameter at all, since Module 5's
    # integration into the risk engine hasn't been finalized. Passing an
    # extra unexpected argument will raise TypeError if the stub
    # signature doesn't include it.
    risk_result = compute_risk_score(ocr_result, validation_result, tamper_result, face_result)

    print("--- authority_result ---")
    print(authority_result)
    print("--- ledger record ---")
    print(write_ledger_record(
        ocr_result, validation_result, tamper_result, face_result, risk_result, authority_result
    ))