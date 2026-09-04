"""
Module 2 — Document Validation.

Public entry point: document_validation(ocr_output, mock_db=None, config=None)
-> dict, matching the Section 9b standardized schema.

During Day 2-3 mock-first integration (Section 9a), the pipeline should
import from `stub` instead of `document_validation` — same function
name and output shape, so swapping the import is the only change
needed once real logic lands.
"""

from .document_validation import (
    DOC_TYPES_CONFIG,
    MOCK_DB_1,
    MockIssuanceDB,
    document_validation,
    is_expiry_valid,
    mrz_checksum_results,
    parse_td3_line2,
    text_mrz_crosscheck,
)
from .checksum import char_value, compute_check_digit, verify_check_digit, verify_composite_check
from .iso3166 import is_valid_country_code

__all__ = [
    "document_validation",
    "MockIssuanceDB",
    "MOCK_DB_1",
    "DOC_TYPES_CONFIG",
    "parse_td3_line2",
    "mrz_checksum_results",
    "text_mrz_crosscheck",
    "is_expiry_valid",
    "compute_check_digit",
    "verify_check_digit",
    "verify_composite_check",
    "char_value",
    "is_valid_country_code",
]
