"""
Module 6a - Hash chain for ledger integrity.
H_n = SHA256(H_{n-1} || record_data)
Protects the ledger's own integrity (detects tampering with stored past
records) - does NOT by itself detect fraud or identity reuse. See
identity_reuse.py for that, and action_plan.pdf Section 4/6 for why these
are deliberately separate mechanisms.
"""

import hashlib
import json

from ...database.ledger_store import get_all_records

GENESIS_HASH = "0" * 64


def compute_record_hash(previous_hash: str, record_data: dict) -> str:
    payload = previous_hash + json.dumps(record_data, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def verify_chain_integrity() -> dict:
    """
    Recomputes every hash in the stored ledger and checks it against
    what's actually recorded — this is what makes tampering with a past
    record DETECTABLE, not just theoretically prevented. Any record
    altered after the fact breaks its own hash and every hash chained
    after it.

    Demo tip: to show this working live, hand-edit one past record's
    JSON value in data/ledger/audit_ledger.json, rerun this function, and
    show it now reports valid=False at that record's index.

    Returns:
      - valid: bool — True only if every record's stored hash matches
        its recomputed hash AND correctly chains to the one before it
      - broken_at_index: int or None — the first record where the chain
        no longer holds, if any
      - total_records: int
    """
    records = get_all_records()
    expected_previous_hash = GENESIS_HASH

    for record in records:
        # Recompute using the same fields that were hashed when the
        # record was written — must exactly match blockchain_ledger.py's
        # record_data shape, or every record will falsely appear broken.
        record_data = {
            "timestamp": record.get("timestamp"),
            "declared_identity": record.get("declared_identity"),
            "declared_doc_number": record.get("declared_doc_number"),
            "risk_result": record.get("risk_result"),
            "face_embedding": record.get("face_embedding"),
            "authority_match_status": record.get("authority_match_status"),
            "authority_match_similarity": record.get("authority_match_similarity"),
        }
        expected_hash = compute_record_hash(expected_previous_hash, record_data)

        if record.get("prev_hash") != expected_previous_hash or record.get("hash") != expected_hash:
            return {
                "valid": False,
                "broken_at_index": record.get("index"),
                "total_records": len(records),
            }

        expected_previous_hash = record["hash"]

    return {"valid": True, "broken_at_index": None, "total_records": len(records)}