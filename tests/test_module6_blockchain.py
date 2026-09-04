"""
Unit tests for Module 6 - Blockchain Ledger.
Test hash_chain.py (6a) and identity_reuse.py (6b) SEPARATELY - they are
different mechanisms, don't test them as one thing.
"""
import pytest


def test_stub_returns_expected_schema():
    from backend.modules.module6_blockchain.stub import write_ledger_record

    result = write_ledger_record({}, {}, {}, {}, {})
    assert result["module"] == "blockchain_ledger"
    assert "record_hash" in result
    assert "previous_hash" in result


def test_hash_chain_breaks_on_tampering():
    from backend.modules.module6_blockchain.hash_chain import compute_record_hash, GENESIS_HASH

    record1 = {"doc": "A"}
    hash1 = compute_record_hash(GENESIS_HASH, record1)

    tampered_record1 = {"doc": "A_ALTERED"}
    hash1_tampered = compute_record_hash(GENESIS_HASH, tampered_record1)

    assert hash1 != hash1_tampered  # altering the record changes its hash


def test_hash_chain_is_deterministic():
    """Same input should always produce the same hash -- required for the
    chain to be verifiable later (re-computing hashes must match stored ones)."""
    from backend.modules.module6_blockchain.hash_chain import compute_record_hash, GENESIS_HASH

    record = {"doc": "A"}
    hash_a = compute_record_hash(GENESIS_HASH, record)
    hash_b = compute_record_hash(GENESIS_HASH, record)
    assert hash_a == hash_b


@pytest.mark.skip(reason="identity_reuse.py does not exist yet -- Module 6b (embedding similarity search) not yet implemented. Un-skip once it lands.")
def test_same_face_different_name_flagged():
    pass


@pytest.mark.skip(reason="identity_reuse.py does not exist yet -- Module 6b (embedding similarity search) not yet implemented. Un-skip once it lands.")
def test_same_face_same_name_not_flagged():
    pass