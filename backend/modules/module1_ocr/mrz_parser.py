"""
mrz_parser.py — MRZ structural parsing for Module 1 (OCR Extraction).

Parses raw MRZ text lines (already OCR'd and restricted to MRZ-safe
characters A-Z0-9< by ocr_extraction.py) into the semantic field VALUES
Module 1's output contract requires: name, passport_number, nationality,
dob (ISO 8601), expiry (ISO 8601), gender. These field names must match
config/doc_types_config.json's expected_fields exactly, since Module 2
(document_validation.py) looks fields up by these names.

DELIBERATELY SEPARATE from Module 2's OWN raw-line re-parsing
(document_validation.py's parse_td3_line2()): this module extracts
human-meaningful VALUES for the OCR output contract (Section 9b); Module 2
needs the raw positional check-digit characters for checksum math
(Section 4 edge case 1) — two genuinely different consumers of the same
44-char MRZ line 2, not redundant logic. as_raw_dict() below preserves
the untouched raw lines specifically so Module 2 can independently
re-derive what it needs without this module having to expose checksum
internals it has no reason to know about.

Currently implements TD3 (passport, 2-line x 44-char) only. TD1
(national ID, 3-line x 30-char) is structurally different and NOT
implemented here — consistent with document_validation.py's own stated
"td1_checksum_not_implemented" limitation; national_id is explicitly a
secondary/generic-OCR-only doc type per config/doc_types_config.json.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional


@dataclass
class MRZField:
    value: Optional[str]


class ParsedMRZ:
    def __init__(self, fields: Dict[str, MRZField], raw_line1: str, raw_line2: str):
        self.fields = fields
        self._raw_line1 = raw_line1
        self._raw_line2 = raw_line2

    def as_raw_dict(self) -> Dict[str, str]:
        """Raw, unparsed MRZ lines. document_validation.py re-parses
        line2 independently to get raw positional check-digit characters
        this class intentionally does not expose (Module 1 has no reason
        to know about checksum math — that's Module 2's job)."""
        return {"line1": self._raw_line1, "line2": self._raw_line2}


def _strip_filler(value: str) -> str:
    """Remove MRZ '<' filler characters, collapsing to a clean string."""
    return value.replace("<", " ").strip()


def _yymmdd_to_iso(yymmdd: str, *, is_expiry: bool) -> Optional[str]:
    """Same ICAO century-pivot convention document_validation.py uses.
    Deliberately reimplemented here rather than imported — these two
    modules parsing the same raw text for different purposes is
    intentional (see module docstring), and this is a 5-line pure
    function, not worth a cross-module dependency for."""
    try:
        yy, mm, dd = int(yymmdd[0:2]), int(yymmdd[2:4]), int(yymmdd[4:6])
    except (ValueError, IndexError):
        return None
    century = 2000 if (is_expiry or yy <= 30) else 1900
    try:
        return date(century + yy, mm, dd).isoformat()
    except ValueError:
        return None


def _parse_td3(lines: List[str]) -> Optional[ParsedMRZ]:
    if len(lines) < 2:
        return None
    line1, line2 = lines[0], lines[1]
    if len(line1) != 44 or len(line2) != 44:
        return None

    # Line 1: P<ISSUING_COUNTRY><SURNAME<<GIVEN<NAMES<<<<<<<<<<<<<<<<<<<<<
    name_field = line1[5:44]
    if "<<" in name_field:
        surname, given = name_field.split("<<", 1)
    else:
        surname, given = name_field, ""
    surname = _strip_filler(surname)
    given = _strip_filler(given)
    full_name = f"{surname} {given}".strip() if given else surname

    # Line 2: fixed-width fields per ICAO 9303 TD3 — same layout
    # document_validation.py's parse_td3_line2() independently parses
    # for checksum purposes.
    doc_number_raw = line2[0:9]
    nationality = line2[10:13]
    dob_raw = line2[13:19]
    sex_char = line2[20]
    expiry_raw = line2[21:27]

    passport_number = _strip_filler(doc_number_raw).replace(" ", "")
    dob_iso = _yymmdd_to_iso(dob_raw, is_expiry=False)
    expiry_iso = _yymmdd_to_iso(expiry_raw, is_expiry=True)
    gender = sex_char if sex_char in ("M", "F") else None

    fields = {
        "name": MRZField(full_name or None),
        "passport_number": MRZField(passport_number or None),
        "nationality": MRZField(nationality.strip() or None),
        "dob": MRZField(dob_iso),
        "expiry": MRZField(expiry_iso),
        "gender": MRZField(gender),
    }
    return ParsedMRZ(fields, raw_line1=line1, raw_line2=line2)


def parse_mrz(lines: List[str], mrz_format: str) -> Optional[ParsedMRZ]:
    """
    lines: MRZ-shaped text lines, already restricted to A-Z0-9< characters
    by ocr_extraction.py before calling this.
    mrz_format: "TD3" (passport) | "TD3_or_none" (visa) | "TD1"
    (national_id, not implemented) | "none" (caller should not call this).

    Returns None (never raises) on malformed/unrecognized input — a bad
    OCR read is a normal condition, not a bug (Section 13).
    """
    if mrz_format in ("TD3", "TD3_or_none"):
        return _parse_td3(lines)
    return None  # TD1 intentionally not implemented — see module docstring