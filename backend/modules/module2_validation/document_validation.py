"""
document_validation.py — Module 2: Document Validation.

Function: verify Module 1's extracted data against format standards,
checksum math, and known-record status. Pure Python, rule-based, no ML
(Section 4).

Depends directly on Module 1's output — cannot run standalone (Section 4
prerequisites). Never raises on bad/partial input: every failure mode
returns a defined status in the output schema instead (Section 13).

CHANGED — full list, this refactor pass:
  1. Fixed absolute imports (`from checksum import ...`) to relative
     (`.checksum`) — the package has an __init__.py, absolute imports
     failed on real import.
  2. Added run_validation() as the actual entry point — routes.py imports
     this name, but only document_validation() existed before.
  3. REMOVED the embedded DOC_TYPES_CONFIG dict — this was a THIRD copy
     of doc-type config in the codebase (alongside config/
     doc_types_config.json and Module 1's own local copy). Now loads
     from the SAME shared loader Module 1 uses
     (backend/modules/shared/doc_types_config_loader.py), which reads
     config/doc_types_config.json, the project's one canonical source.
  4. REMOVED the embedded MOCK_DB_1 / MockIssuanceDB class — this was a
     SEPARATE, differently-shaped duplicate of backend/database/
     mock_db1_issuance.py. Now imports lookup_document_status()
     directly from there.
  5. iso3166.py MOVED to backend/modules/shared/ (general reference data,
     not Module-2-specific logic) — import path updated accordingly.
  6. text_mrz_crosscheck() no longer hardcodes "passport_number" — takes
     id_field_name as a parameter, read from doc_config.
  7. validation_rules is no longer decorative — each doc type's declared
     list in doc_types_config.json now actually gates which checks run.
  8. visa's "expiry_check" rule has no corresponding field in
     expected_fields (only "entry_validation", undocumented semantics) —
     NOT silently guessed. Flagged as "visa_expiry_check_unresolved".
  9. visa's "stay_duration_range_check" has no defined range spec
     anywhere in the project — NOT fabricated. Flagged as
     "stay_duration_check_not_implemented".

Edge cases owned (Section 4):
  1. MRZ checksum verification (7-3-1 weighted formula).
  2. Visible printed text vs. MRZ text cross-check.
  3. Expired / blacklisted document (Mock DB #1).

Output shape is the exact Section 9b stub contract — must not change.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
import re

from .checksum import verify_check_digit, verify_composite_check
from ..shared.iso3166 import is_valid_country_code
from ..shared.doc_types_config_loader import load_doc_types_config
from ...database.mock_db1_issuance import lookup_document_status


# ---------------------------------------------------------------------------
# MRZ parsing — TD3 (passport, 2-line x 44-char) line 2 field layout.
# ---------------------------------------------------------------------------
def parse_td3_line2(line2: str) -> Optional[Dict[str, str]]:
    """Split a TD3 MRZ line 2 into its fixed-width fields per ICAO 9303.
    Returns None (never raises) if the line isn't the expected 44 chars."""
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
    """ICAO century-pivot convention: expiry always future window
    (00-79 -> 20xx), DOB defaults to past (00-30 -> 20xx, 31-99 -> 19xx)."""
    try:
        yy, mm, dd = int(yymmdd[0:2]), int(yymmdd[2:4]), int(yymmdd[4:6])
    except (ValueError, IndexError):
        return None
    century = 2000 if is_expiry else (2000 if yy <= 30 else 1900)
    try:
        return date(century + yy, mm, dd).isoformat()
    except ValueError:
        return None


def mrz_checksum_results(mrz: Dict[str, str]) -> Tuple[Optional[bool], List[str]]:
    """Run every TD3 check digit (Edge case 1). Returns (overall_pass_or_None,
    list_of_failed_field_flags)."""
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
            continue
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


def text_mrz_crosscheck(
    extracted_fields: Dict[str, Any], mrz: Dict[str, str], id_field_name: str
) -> Tuple[bool, List[str]]:
    """Compare Module 1's printed-zone OCR fields against MRZ-parsed
    fields. id_field_name comes from doc_config (was hardcoded to
    "passport_number" before this refactor)."""
    flags: List[str] = []

    printed_doc_num = extracted_fields.get(id_field_name, {}).get("value")
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
# Expiry check — gated by validation_rules, applies where declared.
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
    config: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Module 2 main entry point. Consumes Module 1's exact output schema
    and returns Module 2's exact output schema (Section 9b) — shape must
    not change regardless of internal logic changes."""
    cfg = config or load_doc_types_config()

    result: Dict[str, Any] = {
        "module": "document_validation",
        "status": "failed",
        "checksum_pass": None,
        "text_mrz_match": None,
        "expiry_valid": None,
        "db_status": "not_found",
        "flags": [],
    }

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
    rules = set(doc_config.get("validation_rules", []))

    id_field_name = doc_config["id_field"]
    doc_id = extracted_fields.get(id_field_name, {}).get("value")

    mrz_format = doc_config["mrz_format"]
    mrz_raw = ocr_output.get("mrz_raw") or {}
    mrz_line2 = mrz_raw.get("line2")

    if mrz_format == "none":
        result["checksum_pass"] = None
        result["text_mrz_match"] = None
    elif mrz_format == "TD1":
        result["checksum_pass"] = None
        result["text_mrz_match"] = None
        flags.append("td1_checksum_not_implemented")
    else:
        parsed_mrz = parse_td3_line2(mrz_line2) if mrz_line2 else None
        if parsed_mrz is None:
            if mrz_format == "TD3_or_none":
                result["checksum_pass"] = None
                result["text_mrz_match"] = None
            else:
                result["checksum_pass"] = False
                result["text_mrz_match"] = False
                flags.append("mrz_unreadable")
        else:
            if "checksum" in rules:
                checksum_pass, checksum_flags = mrz_checksum_results(parsed_mrz)
                result["checksum_pass"] = checksum_pass
                flags.extend(checksum_flags)

            if "text_mrz_crosscheck" in rules:
                match_pass, match_flags = text_mrz_crosscheck(extracted_fields, parsed_mrz, id_field_name)
                result["text_mrz_match"] = match_pass
                flags.extend(match_flags)

            if not is_valid_country_code(parsed_mrz.get("nationality", "")):
                flags.append("invalid_country_code")

    if "expiry_check" in rules:
        expiry_value = extracted_fields.get("expiry", {}).get("value") or extracted_fields.get("validity", {}).get("value")
        if expiry_value is None and doc_type == "visa":
            flags.append("visa_expiry_check_unresolved")
            result["expiry_valid"] = None
        else:
            expiry_valid = is_expiry_valid(expiry_value)
            result["expiry_valid"] = expiry_valid
            if expiry_valid is False:
                flags.append("expiry_passed")

    if "stay_duration_range_check" in rules:
        flags.append("stay_duration_check_not_implemented")

    db_status = lookup_document_status(doc_id)
    result["db_status"] = db_status
    if db_status == "blacklisted":
        flags.append("db_blacklisted")
    elif db_status == "expired":
        flags.append("db_expired")
    elif db_status == "not_found":
        flags.append("db_not_found")

    result["flags"] = flags
    # Schema (module2_document_validation) allows only "success" | "failed"
    # — no "partial". The earlier version returned "partial" when Module 1
    # itself only partially succeeded; fixed to match the schema exactly.
    # Fine-grained detail (what specifically didn't check out) already
    # lives in `flags`, so status only needs to mean "validation ran".
    result["status"] = "success"
    return result


def run_validation(ocr_result: Dict[str, Any], doc_type: Optional[str] = None) -> Dict[str, Any]:
    """Public entry point — matches what routes.py actually imports/calls:
        from modules.module2_validation.document_validation import run_validation
        validation_result = run_validation(ocr_result, doc_type)
    doc_type accepted for call-signature compatibility; not required
    internally since document_validation() reads it from ocr_result."""
    return document_validation(ocr_result)

if __name__ == "__main__":

    import os
    from backend.modules.module1_ocr.ocr_extraction import run_ocr

    IMAGE_PATH = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..",
        "data", "fixtures", "clean",
        "clean_passport_01.jpg"
    )

    print("Debug : ", IMAGE_PATH)

    with open(IMAGE_PATH, "rb") as file:
        doc_bytes = file.read()
        
    ocr_result = run_ocr(doc_bytes, "passport")
    print("Debug : ", ocr_result)

    validation_result = run_validation(ocr_result, "passport")

    print(validation_result) 