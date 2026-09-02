"""
Module 6a - Hash chain for ledger integrity.
H_n = SHA256(H_{n-1} || record_data)
Protects the ledger's own integrity (detects tampering with stored past
records) - does NOT by itself detect fraud or identity reuse. See
identity_reuse.py for that, and action_plan.pdf Section 4/6 for why these
are deliberately separate mechanisms.
Owner: fill in during Day 6.
"""

import hashlib
import json

GENESIS_HASH = "0" * 64


def compute_record_hash(previous_hash: str, record_data: dict) -> str:
    payload = previous_hash + json.dumps(record_data, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


# TODO: wire into backend/database/ledger_store.py for append-only storage
