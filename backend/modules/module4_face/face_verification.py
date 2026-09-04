"""
Module 4: Face verification. Same function signature as stub.py's
run_face_verification(). Return schema matches schema/module_io_schema.json
-> module4_face_verification exactly — status is "match" | "mismatch" |
"no_face_detected", not a free-form verdict string.

Threshold from config/thresholds_config.json -> face_verification.match_threshold
(documented there as: cosine SIMILARITY above this = match).

KNOWN LIMITATION this module does NOT close: if a document's photo has
been swapped for the forger's OWN face, done cleanly, this module PASSES
— the live person genuinely matches the (swapped) document photo. That
gap is exactly what Module 5 (Authority Reference Match) exists to close.
"""
import json
import os

from ..shared.face_embedding_utils import get_face_embedding, cosine_similarity

_THRESHOLDS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "config", "thresholds_config.json"
)


def _load_threshold() -> float:
    with open(_THRESHOLDS_PATH) as f:
        return json.load(f)["face_verification"]["match_threshold"]


def run_face_verification(doc_image_bytes: bytes, live_selfie_bytes: bytes) -> dict:
    threshold = _load_threshold()

    doc_result = get_face_embedding(doc_image_bytes)
    selfie_result = get_face_embedding(live_selfie_bytes)

    face_detected_in_document = doc_result["success"]
    face_detected_in_live = selfie_result["success"]

    if not face_detected_in_document or not face_detected_in_live:
        return {
            "module": "face_verification",
            "status": "no_face_detected",
            "similarity": None,
            "threshold_used": threshold,
            "face_detected_in_document": face_detected_in_document,
            "face_detected_in_live": face_detected_in_live,
            "doc_embedding": doc_result["embedding"],  # may still be present even if selfie failed
        }

    similarity = cosine_similarity(doc_result["embedding"], selfie_result["embedding"])
    status = "match" if similarity >= threshold else "mismatch"

    return {
        "module": "face_verification",
        "status": status,
        "similarity": similarity,
        "threshold_used": threshold,
        "face_detected_in_document": True,
        "face_detected_in_live": True,
        # Extra field beyond the base schema, consumed by Module 6b
        # (identity_reuse.py) for cross-checkpoint nearest-neighbor
        # search. Additive/backward-compatible - nothing else breaks if
        # unused. Flagged to the team per blockchain_ledger.py's note.
        "doc_embedding": doc_result["embedding"],
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python face_verification.py <doc_image_path> <selfie_path>")
        sys.exit(1)

    with open(sys.argv[1], "rb") as f:
        doc_bytes = f.read()
    with open(sys.argv[2], "rb") as f:
        selfie_bytes = f.read()

    print(run_face_verification(doc_bytes, selfie_bytes))