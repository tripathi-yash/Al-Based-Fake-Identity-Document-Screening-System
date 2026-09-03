"""
Module 3 combiner — real implementation, replaces stub.py from Day 3+
onward. Same function signature/schema as stub.py's run_tampering_detection.

FUSION LOGIC (this is the architectural decision from the Module 3
critique — see docs/module3_architecture_update.md for the full rationale):

  - ManTraNet (DL) is the PRIMARY signal.
      dl_probability >= high_threshold  -> tampered, high confidence
      dl_probability <= low_threshold   -> clean, high confidence
      in between                        -> BORDERLINE: consult supporting evidence

  - ELA / EXIF / copy-move NEVER get veto power over a confident DL
    verdict. They only resolve borderline DL scores, and if the DL model
    fails to load, they still produce a verdict together (evidence
    strength is lowered accordingly, never silently "clean").

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
    copy_move_result = detect_copy_move(doc_image_bytes)

    support_hits = sum(
        [
            ela_result["ela_score"] > thresholds.get("ela_score_flag_threshold", 0.35),
            exif_result["editing_software_detected"] is not None,
            copy_move_result["copy_move_flag"],
        ]
    )

    if dl_available:
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
