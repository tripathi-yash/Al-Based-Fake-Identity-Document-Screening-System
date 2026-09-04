"""
checksum.py — ICAO Doc 9303 MRZ check-digit computation and verification.

The Machine Readable Zone (MRZ) on passports/visas/national IDs embeds a
check digit after several fields (document number, date of birth, expiry
date, personal number, and a final composite check). Each check digit is
computed with the same 7-3-1 weighted algorithm defined in ICAO Doc 9303.

This module owns ONLY the math. It knows nothing about document layout,
field names, or what to do with a failed check — that logic lives in
document_validation.py. Keeping this pure means it has zero dependencies
and is trivially unit-testable on its own.
"""

from typing import Optional

# ICAO 9303 weight cycle, repeating every 3 characters.
_WEIGHTS = (7, 3, 1)


def char_value(char: str) -> int:
    """
    Map a single MRZ character to its numeric value per ICAO 9303:
      '0'-'9' -> 0-9
      'A'-'Z' -> 10-35
      '<'     -> 0  (filler character)

    Raises ValueError on anything else (should never happen on real MRZ
    text, but we fail loudly here since callers are expected to catch it
    and degrade gracefully rather than let bad input silently compute a
    wrong checksum).
    """
    if char.isdigit():
        return int(char)
    if char == "<":
        return 0
    if char.isalpha() and char.isupper():
        return ord(char) - ord("A") + 10
    raise ValueError(f"Invalid MRZ character: {char!r}")


def compute_check_digit(data: str) -> int:
    """
    Compute the ICAO 9303 check digit for a data string using the
    7-3-1 weighted formula: sum(value(char_i) * weight_i) mod 10.
    """
    total = 0
    for i, ch in enumerate(data):
        total += char_value(ch) * _WEIGHTS[i % 3]
    return total % 10


def verify_check_digit(data: str, check_digit: str) -> Optional[bool]:
    """
    Verify a data field against its printed MRZ check digit.

    Returns:
      True/False — verification result
      None       — check_digit was filler ('<') meaning the field is
                   intentionally unused (e.g. optional personal-number
                   field on some document types); treat as "not
                   applicable", not as a failure.

    Never raises: malformed MRZ (invalid characters, wrong length) is a
    real-world condition (bad scan, damaged document) and must be
    reported as a failed check, not crash the pipeline (Section 13).
    """
    if check_digit == "<":
        return None
    try:
        expected = compute_check_digit(data)
        return expected == int(check_digit)
    except (ValueError, TypeError):
        # Unparseable check digit or invalid MRZ characters — the field
        # cannot be verified, which is functionally a failure.
        return False


def verify_composite_check(fields_with_checks: list, composite_check: str) -> Optional[bool]:
    """
    Verify the final composite check digit on TD3 (passport) MRZ line 2,
    which covers document number+check, DOB+check, expiry+check, and
    optional personal number+check, concatenated together.

    fields_with_checks: list of (data, check_digit) tuples in MRZ order.
    """
    try:
        combined = "".join(data + check for data, check in fields_with_checks)
        return verify_check_digit(combined, composite_check)
    except (ValueError, TypeError, IndexError):
        return False
