"""
Error Level Analysis (Krawetz 2007) — SUPPORTING evidence in the fused
Module 3 pipeline, not the primary detector. See dl_tamper_detector.py for
the primary signal and tampering_detection.py for how these combine.

Vulnerability, stated honestly (say this if asked in Q&A):
ELA's signal weakens if the attacker flattens and recompresses the whole
image after editing — this is exactly why it is not used alone here.
"""
import io
from PIL import Image, ImageChops
import numpy as np


def compute_ela(image_bytes: bytes, resave_quality: int = 90) -> dict:
    """
    Resaves the image at a known JPEG quality and diffs it against the
    original. Returns:
      - ela_score: 0.0-1.0, average magnitude of compression-error anomaly
      - ela_clarity: 0.0-1.0, how uniform/trustworthy this specific reading is
        (heavily recompressed or resized images give a noisy, less
        interpretable map even with nothing to hide — that noisiness itself
        must lower clarity, not silently pass as "clean". See action_plan.pdf
        Section 5, evidence-strength axis.)
      - diff_image: PIL Image, the visual heatmap for the dashboard
    """
    original = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    buffer = io.BytesIO()
    original.save(buffer, "JPEG", quality=resave_quality)
    buffer.seek(0)
    resaved = Image.open(buffer)

    diff = ImageChops.difference(original, resaved)
    diff_arr = np.asarray(diff, dtype=np.float32)

    ela_score = float(diff_arr.mean() / 255.0)

    # Clarity heuristic: a genuinely clean single-generation image gives a
    # LOW, FLAT diff map. A heavily-recompressed/resized image gives a
    # noisy, elevated-everywhere diff map that is hard to interpret as
    # "clean" OR "tampered" with confidence. This ratio-based heuristic is
    # a starting point — tune the exact formula against your fixtures
    # (data/fixtures/clean/ vs a deliberately re-saved/downscaled version
    # of the same image) before trusting it for the demo.
    std = float(diff_arr.std())
    noise_ratio = std / (diff_arr.mean() + 1e-6)
    ela_clarity = float(max(0.0, 1.0 - min(noise_ratio, 5.0) / 5.0))

    # Amplify diff for visualization (raw diff is usually near-black)
    diff_arr_vis = np.clip(diff_arr * 15, 0, 255).astype(np.uint8)
    diff_vis_image = Image.fromarray(diff_arr_vis)

    return {
        "ela_score": ela_score,
        "ela_clarity": ela_clarity,
        "diff_image": diff_vis_image,
    }
