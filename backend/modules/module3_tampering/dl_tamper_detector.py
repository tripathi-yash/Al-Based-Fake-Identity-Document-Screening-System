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
import tempfile
import torch

import gc # Added for active RAM reclamation

# --- CPU Optimization Configs ---
# Restrict PyTorch from hogging all system CPU cores and causing system lag
torch.set_num_threads(2)
torch.set_num_interop_threads(2)

_MODEL = None
_WEIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "mantranet_lib", "MantraNet", "MantraNetv4.pt"
)

# Max target dimension to keep 8GB RAM systems from freezing/swapping
MAX_INFERENCE_DIM = 768  

def _load_model():
    global _MODEL

    if _MODEL is None:
        from .mantranet_lib.MantraNet.mantranet import pre_trained_model

        if not os.path.exists(_WEIGHTS_PATH):
            raise FileNotFoundError(
                f"ManTraNet weights not found at {_WEIGHTS_PATH}. "
                "Complete the one-time setup in this file's docstring first."
            )

        original_cwd = os.getcwd()

        try:
            os.chdir(os.path.dirname(_WEIGHTS_PATH))

            _MODEL = pre_trained_model(
                weight_path=_WEIGHTS_PATH,
                device="cpu"
            )

        finally:
            os.chdir(original_cwd)

    return _MODEL

def detect_tampering_dl(image_bytes: bytes) -> dict:
    """
    Optimized for 8GB RAM / CPU-only execution profiles.
    Downamples target images and restricts core thread utilization.
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
    model = _load_model()

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    orig_w, orig_h = img.size

    # Downsampling calculation to preserve system RAM limits
    if max(orig_w, orig_h) > MAX_INFERENCE_DIM:
        scale = MAX_INFERENCE_DIM / max(orig_w, orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)

    # Transform image into standard tensor format
    im = np.array(img, dtype=np.float32)
    im = torch.Tensor(im)
    im = im.unsqueeze(0)
    im = im.permute(0, 3, 1, 2)  # Structured replacement for multi-.transpose()
    im = im.to("cpu")

    with torch.no_grad():
        final_output = model(im)
        heatmap_arr = final_output[0][0].cpu().detach().numpy()

    # If image was downsampled, upscale the mask back to match original size
    if max(orig_w, orig_h) > MAX_INFERENCE_DIM:
        mask_img = Image.fromarray((heatmap_arr * 255).astype(np.uint8))
        mask_img = mask_img.resize((orig_w, orig_h), Image.Resampling.BILINEAR)
        heatmap_arr = np.array(mask_img, dtype=np.float32) / 255.0

    # Aggregation rule: 90th percentile isolates localized forgery zones
    dl_tamper_probability = float(np.clip(np.percentile(heatmap_arr, 90), 0.0, 1.0))

    # Explicit garbage collection to flush deep model reference graphs from RAM
    del im
    del final_output
    gc.collect()

    # Aggregate to a single probability. A simple mean is a reasonable
    # starting point; consider using the 90th-percentile pixel value
    # instead once you have real fixtures, since a small tampered region
    # in an otherwise clean image should not be diluted by averaging
    # across the whole (mostly clean) image.

    return {
        "dl_tamper_probability": dl_tamper_probability,
        "dl_heatmap": heatmap_arr,
    }

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import time

    start_time = time.perf_counter()
    import matplotlib.pyplot as plt
    example_path = os.path.join(
        os.path.dirname(__file__),
        "mantranet_lib",
        "Demo_images",
        "example.png"
    )
    with open(example_path, "rb") as file:
        image_bytes = file.read()

    print("Starting optimized inference on CPU...")
    result = detect_tampering_dl(image_bytes)

    print("Probability:", result["dl_tamper_probability"])
    print("Heatmap type:", type(result["dl_heatmap"]))
    print("Heatmap shape:", result["dl_heatmap"].shape)
    print("Heatmap min:", result["dl_heatmap"].min())
    print("Heatmap max:", result["dl_heatmap"].max())

    # Load the actual image array for rendering (instead of passing the string path)
    orig_img = Image.open(example_path).convert("RGB")
    orig_arr = np.array(orig_img)

    plt.figure(figsize=(12, 4))

    # Subplot 1: Render the raw input image
    plt.subplot(1, 3, 1)
    plt.imshow(orig_arr)
    plt.title('Original image')

    # Subplot 2: Render the prediction mask
    plt.subplot(1, 3, 2)
    plt.imshow(result["dl_heatmap"], cmap='gray', vmin=0.0, vmax=1.0)
    plt.title('Predicted forgery mask')
    
    # Subplot 3: Fix tensor vs numpy method chaining bug
    plt.subplot(1, 3, 3)
    # Expand dims along axis 2 to match (H, W, 1) for broadcasting against (H, W, 3)
    binary_mask = (result["dl_heatmap"] > 0.2)[:, :, np.newaxis]
    suspicious_regions = orig_arr * binary_mask
    
    plt.imshow(suspicious_regions.astype(np.uint8))
    plt.title('Suspicious regions detected')

    plt.tight_layout()
    plt.show()

    end_time = time.perf_counter()
    print(f"time : {end_time - start_time}:2f")

