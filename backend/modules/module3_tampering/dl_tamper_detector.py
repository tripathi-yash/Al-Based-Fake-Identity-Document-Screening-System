"""
PRIMARY tampering-detection engine: pretrained ManTraNet (Wu et al., CVPR
2019), via the RonyAbecidan/ManTraNet-pytorch port. Outputs a pixel-level
forgery-likelihood heatmap and an aggregate tamper probability.

Be accurate about what this is in your pitch: ManTraNet is a GENERAL
image-forgery localizer (trained on splicing/copy-move/removal/enhancement
across natural images), not a document-specific model. That's still a
legitimate, honest, and much stronger claim than "we use ELA" — say:
"Our primary detection layer is a pretrained deep-learning forgery
localization network, supplemented by classical forensics (ELA, EXIF,
copy-move) for explainability and as independent supporting evidence."

─────────────────────────────────────────────────────────────────────────
ONE-TIME SETUP (do this on Day 3, before writing any code that imports
this file):

    cd backend/modules/module3_tampering
    git clone https://github.com/RonyAbecidan/ManTraNet-pytorch.git mantranet_lib
    pip install torch torchvision opencv-python pillow numpy

  Then follow that repo's README / demo.ipynb to download the pretrained
  weights file (MantraNetv4.pt) into mantranet_lib/MantraNet/.

  IMPORTANT: verify the exact function signature of `check_forgery()` and
  `pre_trained_model()` against that repo's demo.ipynb once you clone it —
  the calls below are based on its documented usage, but confirm the
  return type (heatmap as numpy array vs. matplotlib figure) before relying
  on it, since third-party research repos sometimes change their API
  between commits.

  mantranet_lib/ is vendored, third-party code — do not edit it directly,
  and add it to .gitignore if its weights file is large (it will be).
─────────────────────────────────────────────────────────────────────────
"""
import io
import os
import numpy as np
from PIL import Image

_MODEL = None
_WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "mantranet_lib", "MantraNet", "MantraNetv4.pt"
)


def _load_model():
    global _MODEL
    if _MODEL is None:
        from .mantranet_lib.MantraNet.mantranet import pre_trained_model

        if not os.path.exists(_WEIGHTS_PATH):
            raise FileNotFoundError(
                f"ManTraNet weights not found at {_WEIGHTS_PATH}. "
                "Complete the one-time setup in this file's docstring first."
            )
        _MODEL = pre_trained_model(weight_path=_WEIGHTS_PATH, device="cpu")
    return _MODEL


def detect_tampering_dl(image_bytes: bytes) -> dict:
    """
    Returns:
      - dl_tamper_probability: 0.0-1.0, aggregate forgery likelihood
      - dl_heatmap: numpy array (H x W), per-pixel forgery likelihood,
        for the dashboard's tamper heatmap visualization
    Raises on failure (missing weights, import error) — the caller
    (tampering_detection.py) MUST catch this and fall back to the
    classical-signal-only path, per action_plan.pdf's evidence-strength
    design: a missing primary signal should lower confidence, not crash
    the pipeline.
    """
    from .mantranet_lib.MantraNet.mantranet import check_forgery

    model = _load_model()

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tmp_path = "/tmp/_module3_dl_input.jpg"
    img.save(tmp_path)

    heatmap = check_forgery(model, img_path=tmp_path, device="cpu")
    heatmap_arr = np.asarray(heatmap, dtype=np.float32)

    # Aggregate to a single probability. A simple mean is a reasonable
    # starting point; consider using the 90th-percentile pixel value
    # instead once you have real fixtures, since a small tampered region
    # in an otherwise clean image should not be diluted by averaging
    # across the whole (mostly clean) image.
    dl_tamper_probability = float(np.clip(heatmap_arr.mean(), 0.0, 1.0))

    return {
        "dl_tamper_probability": dl_tamper_probability,
        "dl_heatmap": heatmap_arr,
    }
