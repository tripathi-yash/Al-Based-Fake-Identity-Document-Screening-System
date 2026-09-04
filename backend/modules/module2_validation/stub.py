"""
stub.py — Module 2 Day-2 mock stub (Section 9a, Section 9b).

Same function name/signature the real document_validation() will
eventually have. Returns the exact standardized mock output defined in
Section 9b, unmodified — this is what gets wired into the full
mocked pipeline on Day 2-3, before any real validation logic exists.

Do not add real logic here. Once document_validation.py's real
implementation is ready, the integration layer swaps its import from
`stub.document_validation` to `document_validation.document_validation`
— zero other changes required, because the output schema is identical.
"""

from typing import Any, Dict, Optional


def document_validation(ocr_output: Optional[Dict[str, Any]] = None, **_ignored) -> Dict[str, Any]:
    """Hardcoded Section 9b mock output. Accepts (and ignores) any args
    so it can be dropped into the pipeline with the same call signature
    the real function will use."""
    return {
        "module": "document_validation",
        "status": "success",
        "checksum_pass": True,
        "text_mrz_match": True,
        "expiry_valid": True,
        "db_status": "clear",
        "flags": [],
    }
