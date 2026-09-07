"""
# NOTE: this module deliberately applies NO preprocessing from
# backend/preprocessing/image_preprocess.py — neither normalize_contrast()
# NOR correct_geometry(). Two independent reasons:
#   1. Forensic risk: normalize_contrast() rewrites pixel intensities
#      directly, which would corrupt ELA's recompression-artifact signal.
#      correct_geometry() uses interpolation-based resampling (cv2.warpAffine
#      with INTER_CUBIC), which is gentler but still not strictly
#      pixel-value-preserving — same category of risk, smaller magnitude.
#   2. No functional benefit: ELA has no orientation dependency, SIFT-based
#      copy-move detection is rotation-invariant by design, and ManTraNet
#      has no geometry-normalization assumption baked in. Unlike Module 1
#      (where deskewing measurably improves OCR) or Module 4/5 (where glare
#      normalization measurably reduces face-detection failures), there is
#      no accuracy upside here to weigh against the forensic risk.
# This module intentionally operates on raw uploaded bytes, untouched.

Module 3 combiner — real implementation, replaces stub.py from Day 3+
onward. Same function signature/schema as stub.py's run_tampering_detection.

FUSION LOGIC — UPDATED (Step 3 of the gated Module 3 fix sequence):

  - A RANSAC-verified, RIGID-transform copy-move match (copy_move.py,
    post Step-1 fix: constrained to cv2.estimateAffinePartial2D instead
    of unconstrained homography, PLUS Step-1b spatial compactness filter
    that rejects scattered repeated-font-glyph false positives) is now
    checked FIRST and independently sets tamper_verdict="tampered". This
    is the same non-diluting-floor principle risk_engine/scoring.py
    already applies to Module 5/6b — a confident, geometrically-verified
    signal must not be silently outvoted by an average or vetoed by a
    low DL score.

    This reordering is only safe because Step 1 + Step 1b eliminated the
    two confirmed false-positive sources on the clean fixture (89
    inliers from unconstrained homography fitting repeated MRZ/text
    glyphs, then 59 inliers from repeated font glyphs across text lines
    satisfying a rigid transform at consistent line-spacing) — confirm
    both are resolved on your fixtures before trusting this ordering.

  - ManTraNet (DL) remains the PRIMARY signal for everything copy-move
    does NOT independently confirm.
      dl_probability >= high_threshold  -> tampered, high confidence
      dl_probability <= low_threshold   -> clean, high confidence
      in between                        -> BORDERLINE: consult supporting evidence

  - ELA / EXIF still never get independent veto/confirm power on their
    own — they only resolve borderline DL scores (support_hits >= 2),
    same as before. Only copy_move_flag was promoted to an independent
    floor, because it's the only one of the three supporting signals
    that produces a RANSAC-verified geometric guarantee rather than a
    soft statistical threshold.

  - The output always includes a `tamper_verdict` of "tampered", "clean",
    or "uncertain" — never a forced binary when the evidence doesn't
    support one. "uncertain" should push the risk engine's evidence_band
    to "low", per action_plan.pdf Section 5.
"""
import json
import os

from .dl_tamper_detector import detect_tampering_dl
from .ela import compute_ela
from .exif_check import check_exif
from .copy_move import detect_copy_move

_THRESHOLDS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "config", "thresholds_config.json"
)


def _load_thresholds() -> dict:
    with open(_THRESHOLDS_PATH) as f:
        return json.load(f)["tampering_detection"]


def run_tampering_detection(doc_image_bytes: bytes) -> dict:
    thresholds = _load_thresholds()
    supporting_flags = []

    dl_available = True
    try:
        dl_result = detect_tampering_dl(doc_image_bytes)
        dl_probability = dl_result["dl_tamper_probability"]
    except Exception as e:
        dl_available = False
        dl_probability = None
        supporting_flags.append(f"dl_model_unavailable: {e}")

    ela_result = compute_ela(doc_image_bytes, thresholds.get("ela_quality_resave", 90))
    exif_result = check_exif(doc_image_bytes)

    # NOTE: border_margin_px removed from this call — copy_move.py's
    # Step-1 fix replaced border-masking with a rigid-transform
    # constraint (cv2.estimateAffinePartial2D) that no longer takes a
    # border_margin_px parameter. Passing it now would raise TypeError.
    #
    # NEW (Step 1b): max_cluster_diagonal_fraction now wired from config
    # instead of relying on copy_move.py's hardcoded default — controls
    # how spread out inlier keypoints can be before being rejected as a
    # likely repeated-pattern false positive rather than a genuine
    # localized duplicated region.
    copy_move_result = detect_copy_move(
        doc_image_bytes,
        ratio_thresh=thresholds.get("copy_move_ratio_thresh", 0.75),
        min_spatial_distance_px=thresholds.get("copy_move_min_spatial_distance_px", 20),
        ransac_reproj_thresh=thresholds.get("copy_move_ransac_reproj_thresh", 5.0),
        min_inliers_to_flag=thresholds.get("copy_move_min_inliers_to_flag", 8),
        max_cluster_diagonal_fraction=thresholds.get("copy_move_max_cluster_diagonal_fraction", 0.30),
    )

    support_hits = sum(
        [
            ela_result["ela_score"] > thresholds.get("ela_score_flag_threshold", 0.35),
            exif_result["editing_software_detected"] is not None,
            copy_move_result["copy_move_flag"],
        ]
    )

    # CHANGED (Step 3): a verified rigid copy-move match is checked
    # FIRST and independently confirms tampering — see module docstring
    # for the full rationale and why this reordering is safe post Step 1/1b.
    if copy_move_result["copy_move_flag"]:
        tamper_verdict = "tampered"
        overall_flag = True
        supporting_flags.append("copy_move_verified_duplicate_region")
    elif dl_available:
        high = thresholds.get("dl_high_confidence_threshold", 0.7)
        low = thresholds.get("dl_low_confidence_threshold", 0.3)

        if dl_probability >= high:
            tamper_verdict = "tampered"
            overall_flag = True
        elif dl_probability <= low:
            tamper_verdict = "clean"
            overall_flag = False
        else:
            # Borderline DL score — consult supporting evidence, per the
            # fusion logic in this file's docstring
            if support_hits >= 2:
                tamper_verdict = "tampered"
                overall_flag = True
            else:
                tamper_verdict = "uncertain"
                overall_flag = False
    else:
        # DL unavailable — fall back to classical multi-signal vote.
        # This path should be rare and is a lower-confidence result;
        # evidence_strength in the risk engine should reflect that.
        if support_hits >= 2:
            tamper_verdict = "tampered"
            overall_flag = True
        else:
            tamper_verdict = "uncertain"
            overall_flag = False

    return {
        "module": "tampering_detection",
        "status": "success",
        "dl_tamper_probability": dl_probability,
        "ela_score": ela_result["ela_score"],
        "ela_clarity": ela_result["ela_clarity"],
        "copy_move_flag": copy_move_result["copy_move_flag"],
        "exif_flag": exif_result["editing_software_detected"] is not None,
        "exif_details": exif_result,
        "overall_tamper_flag": overall_flag,
        "tamper_verdict": tamper_verdict,
        "supporting_flags": supporting_flags,
    }

if __name__ == "__main__":
    import os

    example_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..",
        "data",
        "fixtures",
        "tampered",
        "tampered_01_photo_swap.jpg"
    )

    with open(example_path, "rb") as file:
        image_bytes = file.read()

    result = run_tampering_detection(doc_image_bytes=image_bytes)

    print(result)