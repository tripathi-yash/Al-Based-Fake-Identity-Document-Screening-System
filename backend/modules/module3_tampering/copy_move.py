"""
copy_move.py — UPDATED (Step 1b: compactness filter, gated fix sequence).

STEP 1 (done, confirmed): cv2.findHomography -> cv2.estimateAffinePartial2D
dropped clean-fixture false-positive inliers 89 -> 59, and eliminated all
MRZ/border/photo-box matches (confirmed via diagnostic: 0 inliers in
those regions on the clean fixture).

STEP 1b (this change) — NEW EVIDENCE FROM THE SAME DIAGNOSTIC: the
remaining 59 inliers are NOT from MRZ/border/photo — they're ALL in
BODY_TEXT_OR_OTHER, and the recovered transform is a near-pure vertical
shift (dy≈80px, dx≈0). This is the signature of REPEATED FONT GLYPHS
across different text lines at a consistent line-spacing offset — same
letter shapes (e.g. "a", "e", "i") on different printed-field lines
satisfy a rigid transform perfectly, because line-to-line repetition
genuinely IS a rigid translation. Step 1's constraint doesn't rule this
out on its own.

FIX: a genuine copy-move forgery duplicates ONE spatially localized
patch (a stamp, a photo). Its inlier keypoints cluster tightly in both
source and destination. Repeated-glyph false positives, by contrast,
scatter across a large vertical extent of the page (many separate text
lines, not one duplicated region) even though they share one consistent
transform. This adds that missing spatial-locality check on top of the
existing RANSAC geometric-consistency check — RANSAC alone verifies
*a* consistent transform exists; it says nothing about whether the
matched points are localized.

GATE: after this change, confirm on all 3 fixtures — clean's inliers
should now fail the compactness check (cluster too spread out) while
photo_swap and stamp_clone's inliers (genuinely localized duplicated
regions) should stay compact and still flag correctly. Do not tune the
diagonal-fraction threshold below without first re-running the
diagnostic and reporting the real compactness numbers for all 3.
"""
import io
import cv2
import numpy as np
from PIL import Image


def _cluster_diagonal_fraction(points: np.ndarray, image_shape: tuple) -> float:
    """
    Bounding-box diagonal of a point cluster, as a fraction of the full
    image diagonal. Small fraction = tightly clustered (one localized
    patch). Large fraction = scattered across much of the page (many
    separate matches, e.g. repeated font glyphs on different lines).
    """
    if points is None or len(points) == 0:
        return 0.0
    h, w = image_shape[:2]
    xs = points[:, 0]
    ys = points[:, 1]
    box_w = float(xs.max() - xs.min())
    box_h = float(ys.max() - ys.min())
    box_diag = (box_w ** 2 + box_h ** 2) ** 0.5
    img_diag = (float(w) ** 2 + float(h) ** 2) ** 0.5
    return box_diag / img_diag if img_diag > 0 else 0.0


def detect_copy_move(
    image_bytes: bytes,
    ratio_thresh: float = 0.75,
    min_spatial_distance_px: float = 20.0,
    ransac_reproj_thresh: float = 5.0,
    min_inliers_to_flag: int = 8,
    max_cluster_diagonal_fraction: float = 0.30,
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

    transform, inlier_mask = cv2.estimateAffinePartial2D(
        src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=ransac_reproj_thresh
    )
    geometric_inliers = int(inlier_mask.sum()) if inlier_mask is not None else 0

    if geometric_inliers < min_inliers_to_flag:
        return {
            "copy_move_flag": False,
            "match_count": len(good_matches),
            "geometric_inliers": geometric_inliers,
        }

    # NEW (Step 1b): reject if inliers are scattered too widely to be one
    # localized duplicated patch — see module docstring for evidence.
    mask_bool = inlier_mask.ravel().astype(bool)
    inlier_src = src_pts.reshape(-1, 2)[mask_bool]
    inlier_dst = dst_pts.reshape(-1, 2)[mask_bool]

    src_spread = _cluster_diagonal_fraction(inlier_src, gray.shape)
    dst_spread = _cluster_diagonal_fraction(inlier_dst, gray.shape)
    max_spread = max(src_spread, dst_spread)

    if max_spread > max_cluster_diagonal_fraction:
        return {
            "copy_move_flag": False,
            "match_count": len(good_matches),
            "geometric_inliers": geometric_inliers,
            "rejected_reason": "inliers_scattered_likely_repeated_pattern",
            "cluster_diagonal_fraction": round(max_spread, 4),
        }

    flag = geometric_inliers >= min_inliers_to_flag

    return {
        "copy_move_flag": bool(flag),
        "match_count": len(good_matches),
        "geometric_inliers": geometric_inliers,
        "cluster_diagonal_fraction": round(max_spread, 4),
    }


if __name__ == "__main__":
    import os

    example_path = os.path.join(
        os.path.dirname(__file__), "mantranet_lib", "Demo_images", "example.png"
    )
    with open(example_path, "rb") as file:
        image_bytes = file.read()
    print(detect_copy_move(image_bytes=image_bytes))