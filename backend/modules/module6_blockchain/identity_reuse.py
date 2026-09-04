"""
Module 6b - Identity reuse detection via face-embedding nearest-neighbor
search across all previously stored ledger records. SEPARATE mechanism
from hash_chain.py — do not conflate them in explanations or code.

Flags when the same face embedding resurfaces under a different declared
identity/document number across checkpoints. The hash chain does nothing
for this by itself.
"""
from ...database.ledger_store import get_all_records
from ..shared.face_embedding_utils import cosine_similarity


def search_for_identity_reuse(new_embedding, current_name: str, current_doc_number: str) -> dict:
    """
    Returns:
      - identity_reuse_flag: bool
      - identity_reuse_matches: list of prior record IDs (index) where a
        close face match was found under a DIFFERENT declared name or
        document number. Empty when no reuse detected.

    A close match under the SAME name/doc number is expected (the same
    legitimate person screened before) and is never flagged.
    """
    if new_embedding is None:
        return {"identity_reuse_flag": False, "identity_reuse_matches": []}

    records = get_all_records()
    if not records:
        return {"identity_reuse_flag": False, "identity_reuse_matches": []}

    similarity_threshold = 0.6  # see note at bottom re: config wiring

    matches = []
    for record in records:
        stored_embedding = record.get("face_embedding")
        stored_name = record.get("declared_identity")
        stored_doc_number = record.get("declared_doc_number")
        if stored_embedding is None:
            continue

        similarity = cosine_similarity(new_embedding, stored_embedding)
        same_face = similarity >= similarity_threshold
        different_identity = (stored_name != current_name) or (stored_doc_number != current_doc_number)

        if same_face and different_identity:
            matches.append(record.get("index"))

    return {
        "identity_reuse_flag": len(matches) > 0,
        "identity_reuse_matches": matches,
    }

# NOTE: similarity_threshold is hardcoded above pending a decision on
# where it lives in config/thresholds_config.json — it isn't in the
# current file yet. Recommend adding an "identity_reuse_detection":
# {"similarity_threshold": 0.6} block and loading it the same way
# face_verification.py does, before Day 6 wiring.