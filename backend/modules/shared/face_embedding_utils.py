"""
Shared face-embedding utility — used by Module 4, Module 5, and Module 6b
(identity_reuse.py). Centralizing this means all three use the exact same
model, detector backend, and similarity metric.

WHERE THIS SITS:
    backend/modules/shared/face_embedding_utils.py

CONVENTION: returns SIMILARITY (0.0-1.0, higher = more similar), matching
config/thresholds_config.json's documented convention ("cosine similarity
above this = match"). Do not silently switch to distance in a module that
consumes this — every threshold in the config file is written as a
similarity floor, not a distance ceiling.
"""
import os
import tempfile
import numpy as np
from deepface import DeepFace

MODEL_NAME = "Facenet"
DETECTOR_BACKEND = "retinaface"


def _bytes_to_tempfile(image_bytes: bytes, suffix: str = ".jpg") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(image_bytes)
    return path


def get_face_embedding(image_bytes: bytes) -> dict:
    """
    Returns:
      - success: bool
      - embedding: list[float] or None
      - error: str or None ("no_face_detected", "multiple_faces_detected",
        or a wrapped exception message)

    Never raises — callers must check `success` and treat False as
    "evidence unavailable" (per the project's evidence-strength design),
    not as a crash or an automatic no_match/mismatch.
    """
    path = None
    try:
        path = _bytes_to_tempfile(image_bytes)
        result = DeepFace.represent(
            img_path=path,
            model_name=MODEL_NAME,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=True,
        )
        if len(result) == 0:
            return {"success": False, "embedding": None, "error": "no_face_detected"}
        if len(result) > 1:
            return {"success": False, "embedding": None, "error": "multiple_faces_detected"}
        return {"success": True, "embedding": result[0]["embedding"], "error": None}
    except ValueError as e:
        return {"success": False, "embedding": None, "error": f"no_face_detected: {e}"}
    except Exception as e:
        return {"success": False, "embedding": None, "error": f"embedding_extraction_failed: {e}"}
    finally:
        if path and os.path.exists(path):
            os.remove(path)


def cosine_similarity(embedding_a: list, embedding_b: list) -> float:
    """0.0-1.0, higher = more similar. Matches thresholds_config.json's
    documented convention across every module that uses face matching."""
    a = np.asarray(embedding_a, dtype=np.float32)
    b = np.asarray(embedding_b, dtype=np.float32)
    sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)
    return float(np.clip(sim, -1.0, 1.0))