# """
# Two-axis risk scoring engine: risk score (rule violations + tamper/mismatch
# signals) and evidence strength (how much the system actually knew).
# See action_plan.pdf Section 5 for the full design rationale and the
# 2x2 decision matrix (clear / secondary_check / high_risk).
# Weights and band boundaries come from config/thresholds_config.json,
# never hardcode them here.
# Owner: fill in during Day 5-6, after Modules 2/3/4 stubs (or real logic) exist.
# """


# def compute_risk_score(validation_result, tamper_result, face_result, authority_result) -> dict:
#     # TODO: replace with real weighted combination per action_plan.pdf Section 5
#     return {
#         "risk_score": 12,
#         "risk_band": "clear",
#         "evidence_strength": 0.91,
#         "evidence_band": "high",
#         "final_recommendation": "clear",
#         "contributing_flags": [],
#     }

"""
Two-axis risk scoring engine: risk score (rule violations + tamper/mismatch
signals) and evidence strength (how much the system actually knew).
See action_plan.pdf Section 5 for the full design rationale and the
2x2 decision matrix (clear / secondary_check / high_risk).

DESIGN — score + floor, not pure weighted average:
Modules 2/3/4 (validation, tampering, face) are graded/probabilistic
evidence — combined via weighted average, since disagreement between
them is normal and each alone can be wrong at the margins.

Module 5 (authority reference match) and Module 6 (identity reuse) are
different in kind: high-certainty binary signals engineered specifically
to catch fraud patterns the other three CANNOT see by design (a flawless
forgery, or the same face reused under a different identity). A confident
verdict from either must not be diluted by averaging against three clean
signals — same non-dilution principle as Module 3's DL-primary fusion
logic (tampering_detection.py). So they act as a FLOOR on top of the
weighted score, not an additional weighted term:
    final_score = max(weighted_score, floor)
This preserves explainability (the weighted score still reflects the
full picture) while guaranteeing a confident Module 5/6 signal can never
be mathematically outvoted.

Weights and band boundaries come from config/thresholds_config.json,
never hardcoded here.

ASSUMPTION FLAGGED — NOT YET VERIFIED against the real
document_validation.py your teammate wrote: this file assumes
validation_result has a top-level "status" field with values
"valid" | "invalid" | "uncertain", following the same tri-state pattern
every other module in this pipeline uses (tampering: tampered/clean/
uncertain, face: match/mismatch/no_face_detected, authority: match/
mismatch/not_available). If document_validation.py's real schema uses
different field names, update _validation_contribution() below —
everything else in this file is independent of that one assumption.
"""
import json
import os

_THRESHOLDS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "thresholds_config.json"
)


def _load_config() -> dict:
    with open(_THRESHOLDS_PATH) as f:
        return json.load(f)["risk_scoring"]


def _validation_contribution(validation_result: dict) -> tuple[float, bool]:
    """
    Returns (contribution 0.0-1.0, evidence_available bool).

    CORRECTED: originally assumed validation_result["status"] would be
    "valid"/"invalid"/"uncertain" — the real document_validation.py uses
    "status" to mean "did validation COMPLETE" ("success"/"partial"/
    "failed"), not "did the document PASS". The actual pass/fail signal
    lives in checksum_pass, text_mrz_match, expiry_valid, db_status, and
    the flags list. Rewritten to read those instead.
    """
    if validation_result.get("status") == "failed":
        # Upstream OCR failed entirely, or unknown doc_type — no evidence
        # to judge the document on, not the same as "looks invalid".
        return 0.5, False

    flags = validation_result.get("flags", [])
    db_status = validation_result.get("db_status")

    # Hard-fail signals: any of these alone should read as strongly
    # invalid, regardless of what else passed.
    hard_fail_flags = {
        "db_blacklisted", "mrz_unreadable", "invalid_country_code",
        "text_mrz_mismatch_doc_number", "text_mrz_mismatch_dob",
        "text_mrz_mismatch_expiry", "text_mrz_mismatch_nationality",
    }
    checksum_fail_flags = {f for f in flags if f.startswith("checksum_fail_")}

    if db_status == "blacklisted" or any(f in hard_fail_flags for f in flags) or checksum_fail_flags:
        return 1.0, True

    if db_status == "expired" or "expiry_passed" in flags:
        return 0.8, True  # serious, but a slightly softer signal than checksum/blacklist forgery

    if db_status == "not_found":
        # Document isn't in the mock issuance DB at all — ambiguous: could
        # be a real gap in the mock data, not necessarily fraud. Partial
        # evidence, moderate contribution, not a confident fail.
        return 0.4, False

    if validation_result.get("checksum_pass") is False:
        return 1.0, True

    # No fail flags, checksum passed or not applicable, DB clear.
    return 0.0, True


def _tamper_contribution(tamper_result: dict) -> tuple[float, bool]:
    verdict = tamper_result.get("tamper_verdict")
    if verdict == "tampered":
        return 1.0, True
    if verdict == "clean":
        return 0.0, True
    return 0.5, False  # "uncertain"


def _face_contribution(face_result: dict) -> tuple[float, bool]:
    status = face_result.get("status")
    if status == "mismatch":
        return 1.0, True
    if status == "match":
        return 0.0, True
    return 0.5, False  # "no_face_detected"


def compute_risk_score(validation_result, tamper_result, face_result, authority_result, identity_reuse_flag=False) -> dict:
    config = _load_config()
    weights = config["module_weights"]

    val_contrib, val_evidence = _validation_contribution(validation_result)
    tamp_contrib, tamp_evidence = _tamper_contribution(tamper_result)
    face_contrib, face_evidence = _face_contribution(face_result)

    weighted_score = (
        val_contrib * weights["validation_fail"]
        + tamp_contrib * weights["tamper_score"]
        + face_contrib * weights["face_mismatch"]
    ) * 100  # scale to 0-100 to match risk_band_* thresholds

    # --- Floor logic: Module 5 / Module 6 as override signals ---
    floor = 0
    contributing_flags = []
    authority_status = authority_result.get("status") if authority_result else None

    if authority_status == "mismatch":
        floor = max(floor, config.get("override_floor_score", 85))
        contributing_flags.append("authority_reference_mismatch")

    if identity_reuse_flag:
        floor = max(floor, config.get("override_floor_score", 85))
        contributing_flags.append("identity_reuse_detected")

    # Also record softer contributing flags from the weighted signals,
    # for dashboard/audit transparency — these did NOT trigger the floor
    if val_contrib >= 0.75:
        contributing_flags.append("validation_failed")
    if tamp_contrib >= 0.75:
        contributing_flags.append("tampering_detected")
    if face_contrib >= 0.75:
        contributing_flags.append("face_mismatch")

    risk_score = max(weighted_score, floor)
    # Schema (risk_scoring_engine) specifies "0-100 integer" — round()
    # alone returns a float; cast explicitly.
    risk_score = int(round(min(risk_score, 100)))

    # --- Risk band ---
    if risk_score <= config["risk_band_clear_max"]:
        risk_band = "clear"
    elif risk_score <= config["risk_band_secondary_check_max"]:
        risk_band = "secondary_check"
    else:
        risk_band = "high_risk"

    # --- Evidence strength: separate axis from risk score. Reflects how
    # much the system actually knew, not how risky the case looks.
    # authority_result == "not_available" or missing embeddings for
    # identity-reuse checks should LOWER this, never silently pass as
    # high confidence — "we don't know" must stay visibly distinct from
    # "we checked and it's clean". ---
    evidence_flags_known = [val_evidence, tamp_evidence, face_evidence]
    base_evidence_strength = sum(evidence_flags_known) / len(evidence_flags_known)

    if authority_status in (None, "not_available"):
        # Authority match unavailable doesn't ADD evidence, and slightly
        # pulls down overall confidence, but must never be treated as a
        # missing tampering/validation/face signal (weighted differently
        # since Module 5 is a stretch-goal extension, not core evidence).
        evidence_strength = round(base_evidence_strength * 0.9, 2)
    else:
        evidence_strength = round(min(base_evidence_strength * 1.05, 1.0), 2)

    if evidence_strength >= config["evidence_strength_low_threshold"]:
        evidence_band = "high"
    else:
        evidence_band = "low"

    # --- Final recommendation: risk band is primary, but a "clear" band
    # riding on LOW evidence should never be presented as confidently
    # clear — downgrade to secondary_check for a human to review, since
    # "no evidence of fraud" is not the same claim as "evidence of no
    # fraud" (per the project's own founding design principle). ---
    if risk_band == "clear" and evidence_band == "low":
        final_recommendation = "secondary_check"
    else:
        final_recommendation = risk_band

    return {
        "risk_score": risk_score,
        "risk_band": risk_band,
        "evidence_strength": evidence_strength,
        "evidence_band": evidence_band,
        "final_recommendation": final_recommendation,
        "contributing_flags": contributing_flags,
    }
