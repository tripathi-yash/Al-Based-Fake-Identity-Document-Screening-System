"""
Module 5: Authority Reference Match (extension module — build only if
time allows; if cut, present it as a designed extension in the pitch).

Reuses Module 4's face-embedding approach (backend/modules/shared/
face_embedding_utils.py), comparing the document's own current photo
against backend/database/mock_db2_authority_ref.py's stored "authority
original" photo for that passport/ID number.

Closes the flawless-forgery gap: Module 4 passes if a forger swaps in
their own face cleanly (live person matches the swapped photo). Module 5
catches it because the swapped photo no longer matches the authority's
ORIGINAL record for that passport number.

SIGNATURE NOTE — flagging this explicitly rather than silently changing
it: the Day-2 stub.py declares `run_authority_match(ocr_result: dict)`,
but this module needs the document IMAGE to extract a face embedding,
which ocr_result alone does not carry. This real implementation adds
`doc_image_bytes` as a required second parameter. backend/api/routes.py
must be updated to pass `doc_bytes` into this call (it already has
doc_bytes in scope from the upload) — this is a one-line change at the
single call site.

Return schema matches schema/module_io_schema.json ->
module5_authority_reference_match exactly.
"""
import json
import os

from ..shared.face_embedding_utils import get_face_embedding, cosine_similarity
from ...database.mock_db2_authority_ref import get_reference_photo_path

_THRESHOLDS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "config", "thresholds_config.json"
)


def _load_threshold() -> float:
    with open(_THRESHOLDS_PATH) as f:
        thresholds = json.load(f)
        # Falls back to face_verification's threshold if authority_reference_match
        # hasn't been added to the config yet — see note at bottom of this file.
        return thresholds.get("authority_reference_match", {}).get(
            "match_threshold", thresholds["face_verification"]["match_threshold"]
        )


def run_authority_match(ocr_result: dict, doc_image_bytes: bytes) -> dict:
    """
    Returns:
      - module: "authority_reference_match"
      - status: "match" | "mismatch" | "not_available"
      - similarity: 0.0-1.0 or null
      - reference_source: "mock_db_2"

    "not_available" covers: no passport number in ocr_result, no
    authority record for that number, or face extraction failure on
    either image — per schema note, every other module (including the
    risk engine) must work correctly when this returns not_available,
    since Module 5 is a stretch goal that can be cut entirely.
    """
    threshold = _load_threshold()

    passport_number = ocr_result.get("extracted_fields", {}).get("passport_number", {}).get("value")
    if not passport_number:
        return {
            "module": "authority_reference_match",
            "status": "not_available",
            "similarity": None,
            "reference_source": "mock_db_2",
        }

    reference_photo_path = get_reference_photo_path(passport_number)
    if reference_photo_path is None or not os.path.exists(reference_photo_path):
        return {
            "module": "authority_reference_match",
            "status": "not_available",
            "similarity": None,
            "reference_source": "mock_db_2",
        }

    with open(reference_photo_path, "rb") as f:
        reference_bytes = f.read()

    doc_result = get_face_embedding(doc_image_bytes)
    ref_result = get_face_embedding(reference_bytes)

    if not doc_result["success"] or not ref_result["success"]:
        return {
            "module": "authority_reference_match",
            "status": "not_available",
            "similarity": None,
            "reference_source": "mock_db_2",
        }

    similarity = cosine_similarity(doc_result["embedding"], ref_result["embedding"])
    status = "match" if similarity >= threshold else "mismatch"

    return {
        "module": "authority_reference_match",
        "status": status,
        "similarity": similarity,
        "reference_source": "mock_db_2",
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python authority_match.py <doc_image_path>")
        print("(passport_number is read from a fake ocr_result for this smoke test)")
        sys.exit(1)

    with open(sys.argv[1], "rb") as f:
        doc_bytes = f.read()

    fake_ocr_result = {"extracted_fields": {"passport_number": {"value": "P1234567"}}}
    print(run_authority_match(fake_ocr_result, doc_bytes))