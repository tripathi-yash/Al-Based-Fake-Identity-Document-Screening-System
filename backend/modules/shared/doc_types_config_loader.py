"""
Single loader for config/doc_types_config.json — the project's canonical
source of truth for per-doc-type field layout, MRZ format, and validation
rules (Section 11).

Used by BOTH Module 1 (ocr_extraction.py) and Module 2
(document_validation.py) — write once here, import in both, do not
duplicate this loader (or the config data itself) inside either module.
This mirrors the same "shared, not duplicated" principle already applied
to backend/preprocessing/image_preprocess.py and
backend/modules/shared/face_embedding_utils.py.

Loaded lazily (call load_doc_types_config() at call time, not import
time) so a missing/malformed file degrades gracefully per-request instead
of breaking module import for the whole pipeline.
"""
import json
import os

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "config", "doc_types_config.json"
)

# Minimal fallback ONLY used if the canonical file can't be read. If you
# find yourself editing this dict to add/change a doc type, stop — edit
# config/doc_types_config.json instead. This must never become a second
# source of truth.
_FALLBACK_CONFIG = {
    "passport": {
        "mrz_format": "TD3",
        "checksum_required": True,
        "expected_fields": ["name", "passport_number", "nationality", "dob", "expiry", "gender"],
        "validation_rules": ["checksum", "expiry_check", "text_mrz_crosscheck"],
        "id_field": "passport_number",
    },
}


def load_doc_types_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return _FALLBACK_CONFIG