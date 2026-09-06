"""
copy_move.py — UPDATED (Step 1 of the gated Module 3 fix sequence).

CHANGE FROM ORIGINAL: cv2.findHomography (unconstrained, 8 degrees of
freedom: full perspective) replaced with cv2.estimateAffinePartial2D
(rigid: rotation + uniform scale + translation only, 4 DOF).

EVIDENCE (from the confirmed diagnostic on the real fixtures):
  clean_passport_01.jpg (untampered) was producing 89 "geometric
  inliers" under unconstrained homography — a false positive. Repeated
  MRZ filler characters ('<'), repeated glyphs, and straight border
  lines can satisfy a full 8-DOF perspective transform far more easily
  than they can satisfy a rigid, scale-locked transform.

RATIONALE: a genuine copy-paste within the SAME document page is
physically a rigid move — it never undergoes perspective distortion,
since it's the same flat image copied to a new (x,y) offset, not
photographed from a different angle. Constraining the transform to
rigid removes the main source of false-positive matches on repeated
text/borders while a real duplicated region (e.g. a cloned stamp) still
satisfies it perfectly, since it too is a pure translation/rotation of
identical pixels.

GATE BEFORE PROCEEDING TO STEP 2: after this change, re-run the 3-fixture
diagnostic (clean / photo_swap / stamp_clone). Confirm clean's
geometric_inliers drops well below copy_move_min_inliers_to_flag (8)
before touching dl_tamper_detector.py. If it does NOT drop enough,
STOP — report the actual numbers, do not raise the threshold to force
a pass.
"""
import io
import cv2
import numpy as np
from PIL import Image


def detect_copy_move(
    image_bytes: bytes,
    ratio_thresh: float = 0.75,
    min_spatial_distance_px: float = 20.0,
    ransac_reproj_thresh: float = 5.0,
    min_inliers_to_flag: int = 8,
) -> dict:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    sift = cv2.SIFT_create()
    keypoints, descriptors = sift.detectAndCompute(gray, None)

    if descriptors is None or len(keypoints) < min_inliers_to_flag:
        return {"copy_move_flag": False, "match_count": 0, "geometric_inliers": 0}

    bf = cv2.BFMatcher()
    raw_matches = bf.knnMatch(descriptors, descriptors, k=3)

    good_matches = []
    for m in raw_matches:
        if len(m) < 3:
            continue
        _self, candidate, runner_up = m
        if candidate.distance < ratio_thresh * runner_up.distance:
            pt_a = np.array(keypoints[candidate.queryIdx].pt)
            pt_b = np.array(keypoints[candidate.trainIdx].pt)
            if np.linalg.norm(pt_a - pt_b) > min_spatial_distance_px:
                good_matches.append(candidate)

    if len(good_matches) < min_inliers_to_flag:
        return {
            "copy_move_flag": False,
            "match_count": len(good_matches),
            "geometric_inliers": 0,
        }

    src_pts = np.float32(
        [keypoints[m.queryIdx].pt for m in good_matches]
    ).reshape(-1, 1, 2)
    dst_pts = np.float32(
        [keypoints[m.trainIdx].pt for m in good_matches]
    ).reshape(-1, 1, 2)

    # CHANGED: rigid transform instead of unconstrained homography — see
    # module docstring for the evidence/rationale.
    transform, inlier_mask = cv2.estimateAffinePartial2D(
        src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=ransac_reproj_thresh
    )
    geometric_inliers = int(inlier_mask.sum()) if inlier_mask is not None else 0

    flag = geometric_inliers >= min_inliers_to_flag

    return {
        "copy_move_flag": bool(flag),
        "match_count": len(good_matches),
        "geometric_inliers": geometric_inliers,
    }


if __name__ == "__main__":
    import os

    example_path = os.path.join(
        os.path.dirname(__file__), "mantranet_lib", "Demo_images", "example.png"
    )
    with open(example_path, "rb") as file:
        image_bytes = file.read()
    print(detect_copy_move(image_bytes=image_bytes))