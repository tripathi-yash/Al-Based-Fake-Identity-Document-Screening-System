"""
Append-only storage for the blockchain ledger (Module 6). A local JSON
file stands in for real distributed storage in this prototype — say
this plainly if asked. No concurrency handling — sequential processing
only, fine for an 8-9 day prototype/demo.
"""
import json
import os

_LEDGER_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "ledger")
_LEDGER_PATH = os.path.join(_LEDGER_DIR, "audit_ledger.json")


def _load() -> list:
    if not os.path.exists(_LEDGER_PATH):
        return []
    with open(_LEDGER_PATH) as f:
        return json.load(f)


def _save(records: list) -> None:
    os.makedirs(_LEDGER_DIR, exist_ok=True)
    with open(_LEDGER_PATH, "w") as f:
        json.dump(records, f, indent=2)


def append_record(record: dict) -> dict:
    """Appends a fully-formed record (already hashed by hash_chain.py)
    to the ledger and returns it as stored."""
    records = _load()
    record = {**record, "index": len(records)}
    records.append(record)
    _save(records)
    return record


def get_all_records() -> list:
    return _load()


def get_latest_hash() -> str:
    """Returns the most recent record's hash, or hash_chain.GENESIS_HASH
    convention (all-zero) if the ledger is empty. Kept here rather than
    in hash_chain.py since it's a storage-layer read, not hashing logic."""
    records = _load()
    if not records:
        return "0" * 64
    return records[-1]["hash"]