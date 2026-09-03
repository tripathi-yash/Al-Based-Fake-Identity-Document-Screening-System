"""
Copy-move forgery detection via SIFT self-matching — SUPPORTING evidence only.

This is deliberately NOT a naive "count similar keypoints" implementation.
Documents legitimately contain repeated visual patterns (security textures,
borders, repeated glyphs, seals) — a naive matcher flags these as false
positives. This implementation follows the pipeline recommended in the
critique document:

    SIFT keypoints -> ratio test -> spatial-distance filter ->
    RANSAC geometric consistency -> confidence

A genuine copy-paste produces many keypoint matches that agree on ONE
consistent transform (e.g. "everything shifted +100px horizontally").
Random legitimate similarity (e.g. a repeated security pattern) produces
matches with NO consistent transform. RANSAC is what tells these apart.

Vulnerability, stated honestly (say this if asked in Q&A):
This only catches duplication WITHIN the same image. A forger who
generates new content instead of copy-pasting existing content (e.g.
typing new text rather than cloning a digit) produces nothing for this
detector to find — that's a gap this technique cannot close by design,
which is exactly why the DL detector is the primary signal, not this.
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
    # k=3: self-matching means each descriptor's closest match is itself
    # (distance 0) — we need the 2nd and 3rd nearest neighbors for a
    # meaningful ratio test against genuinely DIFFERENT keypoints.
    raw_matches = bf.knnMatch(descriptors, descriptors, k=3)

    good_matches = []
    for m in raw_matches:
        if len(m) < 3:
            continue
        _self, candidate, runner_up = m
        # Lowe's ratio test, applied to the 2nd/3rd neighbor since the
        # 1st is always the trivial self-match
        if candidate.distance < ratio_thresh * runner_up.distance:
            pt_a = np.array(keypoints[candidate.queryIdx].pt)
            pt_b = np.array(keypoints[candidate.trainIdx].pt)
            # discard matches to spatially-adjacent keypoints — these are
            # just neighboring detections on the same real feature, not
            # evidence of duplication elsewhere in the image
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

    homography, inlier_mask = cv2.findHomography(
        src_pts, dst_pts, cv2.RANSAC, ransac_reproj_thresh
    )
    geometric_inliers = int(inlier_mask.sum()) if inlier_mask is not None else 0

    # Only flag if a SINGLE consistent transform explains a meaningful
    # number of matches — this is what distinguishes real copy-move from
    # scattered coincidental similarity across a repeated pattern.
    flag = geometric_inliers >= min_inliers_to_flag

    return {
        "copy_move_flag": bool(flag),
        "match_count": len(good_matches),
        "geometric_inliers": geometric_inliers,
    }
