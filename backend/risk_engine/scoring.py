"""
Two-axis risk scoring engine: risk score (rule violations + tamper/mismatch
signals) and evidence strength (how much the system actually knew).
See action_plan.pdf Section 5 for the full design rationale and the
2x2 decision matrix (clear / secondary_check / high_risk).
Weights and band boundaries come from config/thresholds_config.json,
never hardcode them here.
Owner: fill in during Day 5-6, after Modules 2/3/4 stubs (or real logic) exist.
"""


def compute_risk_score(validation_result, tamper_result, face_result, authority_result) -> dict:
    # TODO: replace with real weighted combination per action_plan.pdf Section 5
    return {
        "risk_score": 12,
        "risk_band": "clear",
        "evidence_strength": 0.91,
        "evidence_band": "high",
        "final_recommendation": "clear",
        "contributing_flags": [],
    }
