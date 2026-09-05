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

try:
    import cv2
    from ...preprocessing.image_preprocess import preprocess_for_face_detection
    _HAS_PREPROCESSING = True
except ImportError:  # pragma: no cover - environment-dependent
    _HAS_PREPROCESSING = False

MODEL_NAME = "Facenet"
DETECTOR_BACKEND = "retinaface"


def _bytes_to_tempfile(image_bytes: bytes, suffix: str = ".jpg") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(image_bytes)
    return path


def _apply_glare_normalization(image_bytes: bytes) -> bytes:
    """Best-effort glare/contrast normalization before face detection —
    unlike Module 3's forensic use case, there's no compression-artifact
    signal here to protect, so this is safe and can measurably reduce
    false no_face_detected results on glare-heavy document photos. Falls
    back to the original bytes unchanged on any failure — never raises,
    never blocks extraction."""
    if not _HAS_PREPROCESSING:
        return image_bytes
    try:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if image is None:
            return image_bytes
        processed = preprocess_for_face_detection(image)
        success, encoded = cv2.imencode(".jpg", processed)
        if not success:
            return image_bytes
        return encoded.tobytes()
    except Exception:
        return image_bytes


def get_face_embedding(image_bytes: bytes, apply_preprocessing: bool = True) -> dict:
    """
    Returns:
      - success: bool
      - embedding: list[float] or None
      - error: str or None ("no_face_detected", "multiple_faces_detected",
        or a wrapped exception message)

    apply_preprocessing (default True): runs glare/contrast normalization
    (backend/preprocessing/image_preprocess.py) before face detection.
    Safe here — unlike Module 3, there's no forensic compression signal
    to protect. Set False if you specifically need the raw bytes (e.g.
    comparing preprocessing's effect during Day 5 threshold tuning).

    Never raises — callers must check `success` and treat False as
    "evidence unavailable" (per the project's evidence-strength design),
    not as a crash or an automatic no_match/mismatch.
    """
    path = None
    try:
        if apply_preprocessing:
            image_bytes = _apply_glare_normalization(image_bytes)

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