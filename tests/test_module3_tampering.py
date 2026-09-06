# """
# Unit tests for Module 3 - Tampering Detection, against REAL source
# (tampering_detection.py, ela.py, exif_check.py, copy_move.py — all
# verified directly, not guessed).

# *** BUG FOUND WHILE WRITING THESE TESTS — READ THIS FIRST ***
# ela.py's compute_ela(), exif_check.py's check_exif(), and copy_move.py's
# detect_copy_move() all call PIL's Image.open() with NO try/except. Only
# the ManTraNet (DL) call inside run_tampering_detection() is wrapped in
# try/except. This means a corrupted/non-image upload will RAISE an
# uncaught PIL.UnidentifiedImageError straight out of run_tampering_detection(),
# which propagates to routes.py's /screen (no try/except there either) and
# will 500 the whole API — violating the "never raise, return status=failed"
# rule that Module 1 (ocr_extraction.py) correctly follows.

# The test below documents this ACTUAL current behavior (it expects the
# raise) rather than asserting the ideal behavior, so this test file stays
# green while accurately telling you where the bug is. FIX RECOMMENDATION:
# wrap the ela_result / exif_result / copy_move_result calls in
# run_tampering_detection() in their own try/except, same pattern already
# used for the DL call, each degrading gracefully and adding to
# supporting_flags on failure. Once fixed, flip
# test_garbage_bytes_currently_raises_KNOWN_BUG below to expect
# status="failed" instead, and delete the xfail marker.
# """
import os
# import pytest

from backend.modules.module3_tampering.tampering_detection import run_tampering_detection

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures")
CLEAN_PASSPORT = os.path.join(FIXTURES_DIR, "clean", "clean_passport_01.jpg")
TAMPERED_PHOTO_SWAP = os.path.join(FIXTURES_DIR, "tampered", "tampered_01_photo_swap.jpg")
TAMPERED_DOB_ALTER = os.path.join(FIXTURES_DIR, "tampered", "tampered_02_dob_alter.jpg")
TAMPERED_STAMP_CLONE = os.path.join(FIXTURES_DIR, "tampered", "tampered_03_stamp_clone.jpg")


# def _skip_if_missing(path):
#     return pytest.mark.skipif(not os.path.isfile(path), reason=f"Fixture not found: {path}")


# def _run_on_file(path):
#     with open(path, "rb") as f:
#         return run_tampering_detection(f.read())


# # ---------------------------------------------------------------------------
# # Contract tests
# # ---------------------------------------------------------------------------
# def test_garbage_bytes_currently_raises_KNOWN_BUG():
#     """
#     Documents ACTUAL behavior, not desired behavior. See module docstring
#     above — this SHOULD return status='failed' but currently raises.
#     If your team fixes the try/except gap before the demo, this test will
#     start FAILING (because no exception is raised anymore) — that's a
#     good failure, meaning the bug is fixed. At that point replace this
#     test with test_garbage_bytes_never_raises (commented below).
#     """
#     with pytest.raises(Exception):
#         run_tampering_detection(b"this is not a valid image")


# # Use this version once the try/except fix is made:
# #
# # def test_garbage_bytes_never_raises():
# #     result = run_tampering_detection(b"this is not a valid image")
# #     assert result["status"] == "failed"


# def test_output_has_all_required_schema_keys_on_valid_image():
#     """Uses a tiny real JPEG (not garbage bytes) so we test schema shape
#     without tripping the known exception bug above."""
#     if not os.path.isfile(CLEAN_PASSPORT):
#         pytest.skip(f"Fixture not found: {CLEAN_PASSPORT}")
#     result = _run_on_file(CLEAN_PASSPORT)
#     for key in ("module", "status", "ela_score", "ela_clarity",
#                 "overall_tamper_flag", "tamper_verdict", "supporting_flags"):
#         assert key in result, f"Missing schema key: {key}"
#     assert result["tamper_verdict"] in ("tampered", "clean", "uncertain")
#     assert isinstance(result["overall_tamper_flag"], bool)
#     assert 0.0 <= result["ela_score"] <= 1.0
#     assert 0.0 <= result["ela_clarity"] <= 1.0
#     if result["dl_tamper_probability"] is not None:
#         assert 0.0 <= result["dl_tamper_probability"] <= 1.0


# # ---------------------------------------------------------------------------
# # Real-fixture tests
# # ---------------------------------------------------------------------------
# @_skip_if_missing(CLEAN_PASSPORT)
# def test_clean_fixture_not_flagged_as_tampered():
#     result = _run_on_file(CLEAN_PASSPORT)
#     assert result["tamper_verdict"] != "tampered", \
#         f"Clean fixture was flagged as tampered — flags: {result.get('supporting_flags')}"


# @_skip_if_missing(TAMPERED_PHOTO_SWAP)
# def test_photo_swap_is_flagged():
#     """Double-JPEG-compression signal — ELA/EXIF should catch this."""
#     result = _run_on_file(TAMPERED_PHOTO_SWAP)
#     assert result["tamper_verdict"] == "tampered", \
#         f"photo_swap fixture NOT flagged — got {result['tamper_verdict']}, flags: {result.get('supporting_flags')}"


# @_skip_if_missing(TAMPERED_STAMP_CLONE)
# def test_stamp_clone_is_flagged():
#     """RANSAC-verified copy-move — geometrically strong signal."""
#     result = _run_on_file(TAMPERED_STAMP_CLONE)
#     assert result["tamper_verdict"] == "tampered", \
#         f"stamp_clone fixture NOT flagged — got {result['tamper_verdict']}"
#     assert result["copy_move_flag"] is True


# @_skip_if_missing(TAMPERED_DOB_ALTER)
# def test_dob_alter_actual_result_is_recorded_not_assumed():
#     """No hard assertion on purpose — this is the ambiguous case flagged
#     earlier (expected_module3_result in the manifest is a PREDICTION,
#     not a verified guarantee). This just prints the real output so your
#     demo narration matches truth."""
#     result = _run_on_file(TAMPERED_DOB_ALTER)
#     print(f"\ntampered_02_dob_alter actual tamper_verdict: {result['tamper_verdict']}")
#     print(f"supporting_flags: {result.get('supporting_flags')}")
#     assert result["tamper_verdict"] in ("tampered", "clean", "uncertain")

# from backend.modules.module3_tampering.tampering_detection import run_tampering_detection
# from backend.modules.module3_tampering.copy_move import detect_copy_move

# for path in [
#     CLEAN_PASSPORT,
#     TAMPERED_PHOTO_SWAP,
#     TAMPERED_STAMP_CLONE,
# ]:
#     with open(path, "rb") as f:
#         b = f.read()
#     result = run_tampering_detection(b)
#     print(path)
#     for k, v in result.items():
#         if k != "dl_heatmap":
#             print(" ", k, "=", v)
#     cm = detect_copy_move(b)
#     print("  raw copy_move:", cm)
#     print()

from backend.modules.module3_tampering.tampering_detection import run_tampering_detection
from backend.modules.module3_tampering.copy_move import detect_copy_move
from backend.modules.module3_tampering.dl_tamper_detector import detect_tampering_dl

# # path = "data/fixtures/clean/clean_passport_01.jpg"
# with open(CLEAN_PASSPORT, "rb") as f:
#     b = f.read()

# result = run_tampering_detection(b)
# for k, v in result.items():
#     if k != "dl_heatmap":
#         print(k, "=", v)

# print("\nraw copy_move:", detect_copy_move(b))
# print("raw dl:", {k: v for k, v in detect_tampering_dl(b).items() if k != "dl_heatmap"})

"""
Run this from the project root:
    python diagnose_clean_false_positive.py
 
Purpose: find out WHERE the copy-move inliers and the DL heatmap's
high-activation region actually are on the clean fixture, before
changing any threshold. Do not skip this — guessing again after the
last regression is how we end up chasing our tail.
"""
import cv2
import numpy as np
from PIL import Image
from scipy import ndimage
import io
 
CLEAN_PATH = CLEAN_PASSPORT
 
 
def diagnose_copy_move_locations(path):
    with open(path, "rb") as f:
        image_bytes = f.read()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
 
    sift = cv2.SIFT_create()
    keypoints, descriptors = sift.detectAndCompute(gray, None)
    bf = cv2.BFMatcher()
    raw_matches = bf.knnMatch(descriptors, descriptors, k=3)
 
    good = []
    for m in raw_matches:
        if len(m) < 3:
            continue
        _self, candidate, runner_up = m
        if candidate.distance < 0.75 * runner_up.distance:
            pt_a = np.array(keypoints[candidate.queryIdx].pt)
            pt_b = np.array(keypoints[candidate.trainIdx].pt)
            if np.linalg.norm(pt_a - pt_b) > 20:
                good.append((pt_a, pt_b, candidate))
 
    if len(good) < 8:
        print("Fewer than 8 good matches — nothing to analyze further.")
        return
 
    src_pts = np.float32([g[0] for g in good]).reshape(-1, 1, 2)
    dst_pts = np.float32([g[1] for g in good]).reshape(-1, 1, 2)
    transform, inlier_mask = cv2.estimateAffinePartial2D(
        src_pts, dst_pts, method=cv2.RANSAC, ransacReprojThreshold=5.0
    )
 
    print(f"Image size: {w}x{h}")
    print(f"Total good matches: {len(good)}, geometric inliers: {int(inlier_mask.sum())}")
    print(f"Affine transform (rotation/scale/translation matrix):\n{transform}\n")
 
    # Bucket inlier keypoints by rough region
    mrz_y_start = int(h * 0.78)  # matches ocr_extraction.py's own MRZ-band assumption
    photo_box = (40, 90, 240, 320)
 
    def classify(pt):
        x, y = pt
        if y >= mrz_y_start:
            return "MRZ"
        if photo_box[0] <= x <= photo_box[2] and photo_box[1] <= y <= photo_box[3]:
            return "PHOTO_BOX"
        if x < 30 or x > w - 30 or y < 30 or y > h - 30:
            return "BORDER"
        return "BODY_TEXT_OR_OTHER"
 
    buckets = {"MRZ": 0, "PHOTO_BOX": 0, "BORDER": 0, "BODY_TEXT_OR_OTHER": 0}
    for i, (pt_a, pt_b, _c) in enumerate(good):
        if inlier_mask[i]:
            buckets[classify(pt_a)] += 1
 
    print("Inlier keypoints by region (source point):")
    for k, v in buckets.items():
        print(f"  {k}: {v}")
 
 
def diagnose_dl_components(path):
    # from modules.module3_tampering.dl_tamper_detector import detect_tampering_dl
 
    with open(path, "rb") as f:
        image_bytes = f.read()
 
    result = detect_tampering_dl(image_bytes)
    heatmap = result["dl_heatmap"]
 
    binary_mask = heatmap >= 0.5
    labeled_array, num_features = ndimage.label(binary_mask)
 
    print(f"\nHeatmap shape: {heatmap.shape}, min={heatmap.min():.3f}, max={heatmap.max():.3f}")
    print(f"Number of connected components >= 0.5 activation: {num_features}")
    print(f"Total image area: {heatmap.size}")
 
    for label_id in range(1, num_features + 1):
        mask = labeled_array == label_id
        area = int(mask.sum())
        if area < 0.001 * heatmap.size:
            continue  # skip tiny noise specks for readability
        ys, xs = np.where(mask)
        mean_score = float(heatmap[mask].mean())
        print(
            f"  component {label_id}: area={area} ({100*area/heatmap.size:.1f}% of image), "
            f"mean_activation={mean_score:.3f}, "
            f"bbox=(x:{xs.min()}-{xs.max()}, y:{ys.min()}-{ys.max()})"
        )
 
 
if __name__ == "__main__":
    print("=" * 70)
    print("COPY-MOVE keypoint location breakdown — clean fixture")
    print("=" * 70)
    diagnose_copy_move_locations(CLEAN_PATH)
 
    print("\n" + "=" * 70)
    print("DL HEATMAP connected-component breakdown — clean fixture")
    print("=" * 70)
    diagnose_dl_components(CLEAN_PATH)
