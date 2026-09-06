"""
Unit tests for Module 6 - Blockchain Ledger, against REAL source
(hash_chain.py, identity_reuse.py, blockchain_ledger.py — all verified
directly). Tests hash_chain (6a) and identity_reuse (6b) SEPARATELY, per
the module's own docstring: they are different mechanisms.

write_ledger_record() and verify_chain_integrity() tests monkeypatch
database.ledger_store so no real ledger file/DB is touched.
"""
import pytest

from backend.modules.module6_blockchain.hash_chain import compute_record_hash, verify_chain_integrity, GENESIS_HASH
from backend.modules.module6_blockchain.identity_reuse import search_for_identity_reuse
from backend.modules.module6_blockchain.blockchain_ledger import write_ledger_record


# ---------------------------------------------------------------------------
# 6a — Hash chain
# ---------------------------------------------------------------------------
def test_hash_is_deterministic_for_same_input():
    record = {"declared_identity": "ASHRAY", "risk_result": {"risk_score": 10}}
    hash_a = compute_record_hash(GENESIS_HASH, record)
    hash_b = compute_record_hash(GENESIS_HASH, record)
    assert hash_a == hash_b


def test_hash_changes_if_record_is_altered():
    """This IS the tamper-evidence property — altering ANY stored field
    must change the hash, proving the audit trail can detect tampering."""
    original = {"declared_identity": "ASHRAY", "risk_result": {"risk_score": 10}}
    altered = {"declared_identity": "ASHRAY", "risk_result": {"risk_score": 99}}
    hash_original = compute_record_hash(GENESIS_HASH, original)
    hash_altered = compute_record_hash(GENESIS_HASH, altered)
    assert hash_original != hash_altered


def test_hash_changes_if_previous_hash_changes():
    """Proves the CHAIN property — same record content, different
    previous_hash, must produce a different hash."""
    record = {"declared_identity": "ASHRAY"}
    hash_a = compute_record_hash(GENESIS_HASH, record)
    hash_b = compute_record_hash("1" * 64, record)
    assert hash_a != hash_b


def test_verify_chain_integrity_valid_on_untampered_ledger(monkeypatch):
    """Build a real 2-record chain by hand (same shape verify_chain_integrity
    recomputes) and confirm it reports valid=True."""
    record_data_1 = {
        "timestamp": "t1", "declared_identity": "ASHRAY", "declared_doc_number": "F1000002",
        "risk_result": {"risk_score": 5}, "face_embedding": [0.1, 0.2],
        "authority_match_status": "match", "authority_match_similarity": 0.9,
        "identity_reuse_flag": False, "identity_reuse_matches": [],
    }
    hash_1 = compute_record_hash(GENESIS_HASH, record_data_1)
    record_1 = {**record_data_1, "prev_hash": GENESIS_HASH, "hash": hash_1, "index": 0}

    record_data_2 = {**record_data_1, "timestamp": "t2", "risk_result": {"risk_score": 8}}
    hash_2 = compute_record_hash(hash_1, record_data_2)
    record_2 = {**record_data_2, "prev_hash": hash_1, "hash": hash_2, "index": 1}

    monkeypatch.setattr(
        "backend.modules.module6_blockchain.hash_chain.get_all_records",
        lambda: [record_1, record_2],
    )
    result = verify_chain_integrity()
    assert result["valid"] is True
    assert result["broken_at_index"] is None
    assert result["total_records"] == 2


def test_verify_chain_integrity_detects_tampering(monkeypatch):
    """Demo-worthy: hand-edit one stored field after the hash was computed
    -> chain must report valid=False. This is the live 'tamper the ledger'
    demo moment hash_chain.py's own docstring suggests."""
    record_data_1 = {
        "timestamp": "t1", "declared_identity": "ASHRAY", "declared_doc_number": "F1000002",
        "risk_result": {"risk_score": 5}, "face_embedding": [0.1, 0.2],
        "authority_match_status": "match", "authority_match_similarity": 0.9,
        "identity_reuse_flag": False, "identity_reuse_matches": [],
    }
    hash_1 = compute_record_hash(GENESIS_HASH, record_data_1)
    record_1 = {**record_data_1, "prev_hash": GENESIS_HASH, "hash": hash_1, "index": 0}

    # Simulate someone hand-editing the stored record AFTER hashing —
    # risk_score changed from 5 to 0, hash left as-is (the attack).
    tampered_record_1 = {**record_1, "risk_result": {"risk_score": 0}}

    monkeypatch.setattr(
        "backend.modules.module6_blockchain.hash_chain.get_all_records",
        lambda: [tampered_record_1],
    )
    result = verify_chain_integrity()
    assert result["valid"] is False
    assert result["broken_at_index"] == 0


# ---------------------------------------------------------------------------
# 6b — Identity reuse
# ---------------------------------------------------------------------------
FACE_A = [0.9, 0.1, 0.0, 0.0]  # stand-in embeddings; only relative similarity matters
FACE_B = [0.0, 0.0, 0.9, 0.1]  # clearly different face


def test_no_reuse_when_no_prior_records(monkeypatch):
    monkeypatch.setattr(
        "backend.modules.module6_blockchain.identity_reuse.get_all_records",
        lambda: [],
    )
    result = search_for_identity_reuse(FACE_A, "ASHRAY", "F1000002")
    assert result["identity_reuse_flag"] is False
    assert result["identity_reuse_matches"] == []


def test_same_face_same_identity_not_flagged(monkeypatch):
    """Same legitimate person screened before — expected, never flagged."""
    prior_records = [{
        "index": 1, "face_embedding": FACE_A,
        "declared_identity": "ASHRAY", "declared_doc_number": "F1000002",
    }]
    monkeypatch.setattr(
        "backend.modules.module6_blockchain.identity_reuse.get_all_records",
        lambda: prior_records,
    )
    result = search_for_identity_reuse(FACE_A, "ASHRAY", "F1000002")
    assert result["identity_reuse_flag"] is False


def test_same_face_different_identity_is_flagged(monkeypatch):
    """THE core 6b catch: same face embedding resurfaces under a
    fabricated new identity/doc number."""
    prior_records = [{
        "index": 1, "face_embedding": FACE_A,
        "declared_identity": "ASHRAY", "declared_doc_number": "F1000002",
    }]
    monkeypatch.setattr(
        "backend.modules.module6_blockchain.identity_reuse.get_all_records",
        lambda: prior_records,
    )
    result = search_for_identity_reuse(FACE_A, "RAHUL", "F9999999")
    assert result["identity_reuse_flag"] is True
    assert 1 in result["identity_reuse_matches"]


def test_different_face_different_identity_not_flagged(monkeypatch):
    """Sanity check: a genuinely different person under a new identity
    must NOT be flagged — otherwise 6b would flag every new applicant."""
    prior_records = [{
        "index": 1, "face_embedding": FACE_A,
        "declared_identity": "ASHRAY", "declared_doc_number": "F1000002",
    }]
    monkeypatch.setattr(
        "backend.modules.module6_blockchain.identity_reuse.get_all_records",
        lambda: prior_records,
    )
    result = search_for_identity_reuse(FACE_B, "RIYA", "F1000003")
    assert result["identity_reuse_flag"] is False


def test_none_embedding_never_flags():
    result = search_for_identity_reuse(None, "ASHRAY", "F1000002")
    assert result["identity_reuse_flag"] is False
    assert result["identity_reuse_matches"] == []


# ---------------------------------------------------------------------------
# write_ledger_record() — full combiner, DB calls monkeypatched
# ---------------------------------------------------------------------------
def test_write_ledger_record_persists_authority_and_reuse_fields(monkeypatch):
    stored = {}

    def fake_append_record(record):
        stored.update(record)
        return {**record, "timestamp": "2026-09-05T00:00:00Z"}

    monkeypatch.setattr(
        "backend.modules.module6_blockchain.blockchain_ledger.append_record", fake_append_record
    )
    monkeypatch.setattr(
        "backend.modules.module6_blockchain.blockchain_ledger.get_latest_hash", lambda: GENESIS_HASH
    )

    ocr_result = {"extracted_fields": {
        "name": {"value": "ASHRAY"}, "passport_number": {"value": "F1000002"}
    }}
    face_result = {"doc_embedding": FACE_A}
    authority_result = {"status": "mismatch", "similarity": 0.2}
    identity_reuse_result = {"identity_reuse_flag": True, "identity_reuse_matches": [1]}

    ledger_record = write_ledger_record(
        ocr_result, {}, {}, face_result, {"risk_score": 90},
        authority_result, identity_reuse_result,
    )

    assert ledger_record["status"] == "success"
    assert ledger_record["authority_match_status"] == "mismatch"
    assert ledger_record["identity_reuse_flag"] is True
    # confirm these were actually PERSISTED into record_data, not just
    # returned transiently — the exact bug this file's docstring says was fixed
    assert stored["authority_match_status"] == "mismatch"
    assert stored["identity_reuse_flag"] is True