"""
document_validation.py — Module 2: Document Validation.

Function: verify Module 1's extracted data against format standards,
checksum math, and known-record status. Pure Python, rule-based, no ML
(Section 4).

Depends directly on Module 1's output — cannot run standalone (Section 4
prerequisites). Never raises on bad/partial input: every failure mode
returns a defined status in the output schema instead (Section 13).

Edge cases owned (Section 4):
  1. MRZ checksum verification (7-3-1 weighted formula) — catches
     physical alteration where the MRZ check digit wasn't recomputed.
  2. Visible printed text vs. MRZ text cross-check — catches physical
     alteration where one zone (printed or MRZ) was updated and the
     other wasn't.
  3. Expired / blacklisted document — catches a genuinely clean
     document that is simply invalid per records (Mock DB #1),
     independent of any image analysis.

Output shape is the exact Section 9b stub contract — real logic here
must never deviate from it; that contract is what lets the rest of the
pipeline (already integrated against the mock stub) keep working
unchanged once this file replaces stub.py's Module 2 function.
"""

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from checksum import verify_check_digit, verify_composite_check
from iso3166 import is_valid_country_code

# ---------------------------------------------------------------------------
# Section 11 — multi-document-type config (source of truth for how each doc
# type is validated). In production this lives in doc_types_config.json;
# embedded here so the module has no external file dependency out of the box.
# ---------------------------------------------------------------------------
DOC_TYPES_CONFIG: Dict[str, Dict[str, Any]] = {
    "passport": {
        "mrz_format": "TD3",
        "checksum_required": True,
        "expected_fields": ["name", "passport_number", "nationality", "dob", "expiry", "gender"],
        "validation_rules": ["checksum", "expiry_check", "text_mrz_crosscheck"],
        "id_field": "passport_number",
    },
    "visa": {
        "mrz_format": "TD3_or_none",
        "checksum_required": False,
        "expected_fields": ["visa_number", "visa_type", "entry_validation", "stay_duration"],
        "validation_rules": ["expiry_check", "stay_duration_range_check"],
        "id_field": "visa_number",
    },
    "national_id": {
        "mrz_format": "TD1",
        "checksum_required": True,
        "expected_fields": ["name", "id_number", "dob"],
        "validation_rules": ["checksum"],
        "id_field": "id_number",
    },
    "driving_license": {
        "mrz_format": "none",
        "checksum_required": False,
        "expected_fields": ["name", "license_number", "dob", "expiry"],
        "validation_rules": ["expiry_check"],
        "id_field": "license_number",
    },
    "permit": {
        "mrz_format": "none",
        "checksum_required": False,
        "expected_fields": ["name", "permit_number", "validity"],
        "validation_rules": ["expiry_check"],
        "id_field": "permit_number",
    },
}

# ---------------------------------------------------------------------------
# Mock DB #1 — Issuance/Blacklist table (Section 4 prerequisite, Section 12
# task allocation). 5-10 entries; some drawn from the MIDV-500 subset actually
# used for fixtures, some invented. IDs here MUST match fixture IDs exactly —
# a single typo silently breaks Module 2 tests (Section 12 golden rule).
# Real deployment: same lookup interface, backed by a live government
# issuance/blacklist system instead of this dict (Section 7).
# ---------------------------------------------------------------------------
MOCK_DB_1: Dict[str, str] = {
    # passport_number / visa_number / id_number -> "issued" | "expired" | "blacklisted"
    "P1234567": "issued",
    "P7654321": "blacklisted",
    "P1122334": "expired",
    "P9988776": "issued",
    "V5566778": "issued",
    "V2233445": "blacklisted",
    "N4455667": "issued",
    "N7788990": "expired",
}

_DB_STATUS_MAP = {
    "issued": "clear",
    "expired": "expired",
    "blacklisted": "blacklisted",
}


class MockIssuanceDB:
    """Thin lookup wrapper so document_validation() doesn't touch the raw
    dict directly — makes it a one-line swap to a real DB client later."""

    def __init__(self, table: Optional[Dict[str, str]] = None):
        self._table = table if table is not None else MOCK_DB_1

    def lookup(self, doc_id: Optional[str]) -> str:
        """Returns 'clear' | 'blacklisted' | 'expired' | 'not_found'."""
        if not doc_id:
            return "not_found"
        raw_status = self._table.get(doc_id.strip().upper())
        if raw_status is None:
            return "not_found"
        return _DB_STATUS_MAP.get(raw_status, "not_found")


# ---------------------------------------------------------------------------
# MRZ parsing — TD3 (passport, 2-line x 44-char) line 2 field layout.
# ---------------------------------------------------------------------------
def parse_td3_line2(line2: str) -> Optional[Dict[str, str]]:
    """
    Split a TD3 MRZ line 2 into its fixed-width fields per ICAO 9303.
    Returns None (never raises) if the line isn't the expected 44 chars —
    a damaged/misread MRZ is a real condition, not a bug.
    """
    if not line2 or len(line2) != 44:
        return None
    return {
        "doc_number": line2[0:9],
        "doc_number_check": line2[9],
        "nationality": line2[10:13],
        "dob": line2[13:19],
        "dob_check": line2[19],
        "sex": line2[20],
        "expiry": line2[21:27],
        "expiry_check": line2[27],
        "personal_number": line2[28:42],
        "personal_number_check": line2[42],
        "composite_check": line2[43],
    }


def _yymmdd_to_iso(yymmdd: str, *, is_expiry: bool) -> Optional[str]:
    """Convert MRZ 6-digit YYMMDD to ISO 8601, with ICAO's century pivot:
    expiry dates are always in the future window (00-79 -> 20xx by
    convention for expiry), DOB defaults to the past (00-30 -> 20xx,
    31-99 -> 19xx) — a documented heuristic, not a guarantee."""
    try:
        yy, mm, dd = int(yymmdd[0:2]), int(yymmdd[2:4]), int(yymmdd[4:6])
    except (ValueError, IndexError):
        return None
    if is_expiry:
        century = 2000
    else:
        century = 2000 if yy <= 30 else 1900
    try:
        return date(century + yy, mm, dd).isoformat()
    except ValueError:
        return None


def mrz_checksum_results(mrz: Dict[str, str]) -> Tuple[Optional[bool], List[str]]:
    """
    Run every TD3 check digit (Edge case 1: 7-3-1 checksum verification).
    Returns (overall_pass_or_None, list_of_failed_field_flags).
    overall is None only if every relevant check digit was filler (should
    not happen for doc_number/dob/expiry on a real passport).
    """
    flags: List[str] = []
    results: List[bool] = []

    checks = [
        ("doc_number", mrz["doc_number"], mrz["doc_number_check"], "checksum_fail_doc_number"),
        ("dob", mrz["dob"], mrz["dob_check"], "checksum_fail_dob"),
        ("expiry", mrz["expiry"], mrz["expiry_check"], "checksum_fail_expiry"),
        ("personal_number", mrz["personal_number"], mrz["personal_number_check"], "checksum_fail_personal_number"),
    ]
    for _name, data, check_digit, flag in checks:
        result = verify_check_digit(data, check_digit)
        if result is None:
            continue  # filler check digit, field not in use — not a failure
        results.append(result)
        if not result:
            flags.append(flag)

    composite = verify_composite_check(
        [
            (mrz["doc_number"], mrz["doc_number_check"]),
            (mrz["dob"], mrz["dob_check"]),
            (mrz["expiry"], mrz["expiry_check"]),
            (mrz["personal_number"], mrz["personal_number_check"]),
        ],
        mrz["composite_check"],
    )
    if composite is not None:
        results.append(composite)
        if not composite:
            flags.append("checksum_fail_composite")

    if not results:
        return None, flags
    return all(results), flags


# ---------------------------------------------------------------------------
# Edge case 2 — visible printed text vs. MRZ text cross-check.
# ---------------------------------------------------------------------------
def _normalize(text: Optional[str]) -> str:
    if not text:
        return ""
    return re.sub(r"[^A-Z0-9]", "", text.strip().upper())


def text_mrz_crosscheck(extracted_fields: Dict[str, Any], mrz: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    Compare Module 1's printed-zone OCR fields against the MRZ-parsed
    fields for the same document. A mismatch means one zone was edited
    (e.g. printed DOB altered) without recomputing the other — exactly
    the physical-alteration pattern this check exists to catch
    (Section 4, Section 6 fraud-scenario matrix).
    """
    flags: List[str] = []

    printed_doc_num = extracted_fields.get("passport_number", {}).get("value")
    if printed_doc_num is not None and _normalize(printed_doc_num) != _normalize(mrz["doc_number"]):
        flags.append("text_mrz_mismatch_doc_number")

    printed_dob = extracted_fields.get("dob", {}).get("value")
    mrz_dob_iso = _yymmdd_to_iso(mrz["dob"], is_expiry=False)
    if printed_dob is not None and mrz_dob_iso is not None and printed_dob != mrz_dob_iso:
        flags.append("text_mrz_mismatch_dob")

    printed_expiry = extracted_fields.get("expiry", {}).get("value")
    mrz_expiry_iso = _yymmdd_to_iso(mrz["expiry"], is_expiry=True)
    if printed_expiry is not None and mrz_expiry_iso is not None and printed_expiry != mrz_expiry_iso:
        flags.append("text_mrz_mismatch_expiry")

    printed_nationality = extracted_fields.get("nationality", {}).get("value")
    if printed_nationality is not None and _normalize(printed_nationality) != _normalize(mrz["nationality"]):
        flags.append("text_mrz_mismatch_nationality")

    return (len(flags) == 0), flags


# ---------------------------------------------------------------------------
# Expiry check — applies to every doc type (Section 11).
# ---------------------------------------------------------------------------
def is_expiry_valid(expiry_iso: Optional[str], *, today: Optional[date] = None) -> Optional[bool]:
    if not expiry_iso:
        return None
    try:
        expiry_date = datetime.strptime(expiry_iso, "%Y-%m-%d").date()
    except ValueError:
        return None
    return expiry_date >= (today or date.today())


# ---------------------------------------------------------------------------
# Main entry point.
# ---------------------------------------------------------------------------
def document_validation(
    ocr_output: Dict[str, Any],
    mock_db: Optional[MockIssuanceDB] = None,
    config: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Module 2 main entry point. Consumes Module 1's exact output schema
    (Section 9b) and returns Module 2's exact output schema (Section 9b) —
    the shape must not change regardless of internal logic changes, real
    or mocked, per the mock-first integration strategy (Section 9a).
    """
    db = mock_db or MockIssuanceDB()
    cfg = config or DOC_TYPES_CONFIG

    result: Dict[str, Any] = {
        "module": "document_validation",
        "status": "failed",
        "checksum_pass": None,
        "text_mrz_match": None,
        "expiry_valid": None,
        "db_status": "not_found",
        "flags": [],
    }

    # Module 1 failed outright — nothing to validate (never crash, Section 13).
    if not ocr_output or ocr_output.get("status") == "failed":
        result["flags"].append("upstream_ocr_failed")
        return result

    doc_type = ocr_output.get("doc_type")
    doc_config = cfg.get(doc_type)
    if doc_config is None:
        result["flags"].append("unknown_doc_type")
        return result

    extracted_fields = ocr_output.get("extracted_fields", {}) or {}
    flags: List[str] = []

    # --- doc-type-appropriate ID field lookup (Section 11 dispatch) -------
    id_field_name = doc_config["id_field"]
    doc_id = extracted_fields.get(id_field_name, {}).get("value")

    # --- MRZ-dependent checks (checksum + cross-check), dispatched by
    # config, per Section 11: only run where mrz_format actually applies.
    mrz_format = doc_config["mrz_format"]
    mrz_raw = ocr_output.get("mrz_raw") or {}
    mrz_line2 = mrz_raw.get("line2")

    if mrz_format == "none":
        # Explicitly null, not defaulted to True (Section 9b requirement).
        result["checksum_pass"] = None
        result["text_mrz_match"] = None
    elif mrz_format == "TD1":
        # TD1 (national ID) MRZ is a 3-line x 30-char layout, structurally
        # different from TD3 — not implemented in this prototype. Stated
        # limitation, not a silent gap: national ID is explicitly a
        # secondary/generic-OCR-only doc type (Section 11), so we report
        # this honestly rather than misreport it as a scan-quality issue.
        result["checksum_pass"] = None
        result["text_mrz_match"] = None
        flags.append("td1_checksum_not_implemented")
    else:
        parsed_mrz = parse_td3_line2(mrz_line2) if mrz_line2 else None
        if parsed_mrz is None:
            if mrz_format == "TD3_or_none":
                # Visa without an MRZ is valid by design — not a failure.
                result["checksum_pass"] = None
                result["text_mrz_match"] = None
            else:
                # MRZ was expected (TD3 passport) but unreadable/malformed —
                # flag it, don't silently pass.
                result["checksum_pass"] = False
                result["text_mrz_match"] = False
                flags.append("mrz_unreadable")
        else:
            checksum_pass, checksum_flags = mrz_checksum_results(parsed_mrz)
            match_pass, match_flags = text_mrz_crosscheck(extracted_fields, parsed_mrz)
            result["checksum_pass"] = checksum_pass
            result["text_mrz_match"] = match_pass
            flags.extend(checksum_flags)
            flags.extend(match_flags)

            if not is_valid_country_code(parsed_mrz.get("nationality", "")):
                flags.append("invalid_country_code")

    # --- expiry check (applies to every doc type) --------------------------
    expiry_value = extracted_fields.get("expiry", {}).get("value") or extracted_fields.get("validity", {}).get("value")
    expiry_valid = is_expiry_valid(expiry_value)
    result["expiry_valid"] = expiry_valid
    if expiry_valid is False:
        flags.append("expiry_passed")

    # --- Mock DB #1 lookup (Edge case 3: expired/blacklisted record) -------
    db_status = db.lookup(doc_id)
    result["db_status"] = db_status
    if db_status == "blacklisted":
        flags.append("db_blacklisted")
    elif db_status == "expired":
        flags.append("db_expired")
    elif db_status == "not_found":
        flags.append("db_not_found")

    result["flags"] = flags
    result["status"] = "success" if ocr_output.get("status") == "success" else "partial"
    return result
