# """
# Unit tests for Module 1 - OCR Extraction, against the REAL
# modules/module1_ocr/ocr_extraction.py (not stub.py — the old test file
# pointed at backend.modules.module1_ocr.stub, which no longer matches
# your project layout or the real implementation).

# Two layers of tests here:
#   1. Contract tests that don't need a real image (garbage bytes / unknown
#      doc_type) — these are deterministic regardless of whether
#      PaddleOCR/EasyOCR/pytesseract is installed.
#   2. Real-fixture tests (skipped automatically if the fixture file isn't
#      found at the path below) — adjust FIXTURES_DIR to match your layout.
# """
# import os
# import re
# import pytest

# from backend.modules.module1_ocr.ocr_extraction import run_ocr

# FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures")
# # data\fixtures\clean\25_grc_passport\images\CA\CA25_01.jpg
# # CLEAN_PASSPORT = os.path.join(FIXTURES_DIR, "clean","25_grc_passport","images", "CA", "CA25_01.jpg")
# # data\fixtures\clean\23_fin_drvlic\images\CA\CA23_01.jpg
# CLEAN_PASSPORT = os.path.join(FIXTURES_DIR, "clean","23_fin_drvlic","images", "CA", "CA23_01.jpg")
# # CLEAN_PASSPORT = os.path.join(FIXTURES_DIR, "clean", "clean_passport_01.jpg")

# ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# skip_if_missing = pytest.mark.skipif(
#     not os.path.isfile(CLEAN_PASSPORT),
#     reason=f"Fixture not found at {CLEAN_PASSPORT} — adjust FIXTURES_DIR at top of this file",
# )


# # ---------------------------------------------------------------------------
# # Contract tests — no real image needed, always runnable
# # ---------------------------------------------------------------------------
# def test_unknown_doc_type_fails_without_guessing():
#     """run_ocr must return failed immediately for an unregistered doc_type,
#     per the module's own docstring: 'unknown doc_type -> failed, don't guess'."""
#     result = run_ocr(b"irrelevant bytes", "not_a_real_doc_type")
#     assert result["status"] == "failed"
#     assert result["extracted_fields"] == {}


# def test_garbage_bytes_never_raises_and_fails_gracefully():
#     """Section 9b/13 hard rule: never raise out of run_ocr() for a bad image."""
#     result = run_ocr(b"this is not a valid jpeg", "passport")
#     assert result["status"] == "failed"
#     assert result["extracted_fields"] == {}


# def test_empty_bytes_never_raises():
#     result = run_ocr(b"", "passport")
#     assert result["status"] in ("failed", "partial", "success")  # must not raise


# def test_output_always_has_required_top_level_keys():
#     result = run_ocr(b"garbage", "passport")
#     for key in ("module", "doc_type", "status", "extracted_fields"):
#         assert key in result
#     assert result["module"] == "ocr_extraction"
#     assert result["status"] in ("success", "partial", "failed")


# # ---------------------------------------------------------------------------
# # Real-fixture tests — require an actual image + at least one OCR backend
# # installed (paddleocr / easyocr / pytesseract). If no backend is
# # installed, extracted_fields may come back mostly empty via the MRZ path
# # only (if passporteye is present) — these tests check STRUCTURE and
# # ISO date formatting, not that every field was found, since OCR accuracy
# # depends on your environment's installed engines.
# # ---------------------------------------------------------------------------
# @skip_if_missing
# def test_clean_passport_returns_some_extracted_fields():
#     with open(CLEAN_PASSPORT, "rb") as f:
#         image_bytes = f.read()
#     result = run_ocr(image_bytes, "passport")
#     assert result["status"] in ("success", "partial"), (
#         f"Expected success/partial on a clean fixture, got '{result['status']}' — "
#         "check that an OCR backend (paddleocr/easyocr/pytesseract) is installed."
#     )
#     assert len(result["extracted_fields"]) > 0


# @skip_if_missing
# def test_every_extracted_field_has_value_and_confidence_in_range():
#     with open(CLEAN_PASSPORT, "rb") as f:
#         image_bytes = f.read()
#     result = run_ocr(image_bytes, "passport")
#     for field_name, field in result["extracted_fields"].items():
#         assert "value" in field, f"Field '{field_name}' missing 'value'"
#         assert "confidence" in field, f"Field '{field_name}' missing 'confidence'"
#         assert 0.0 <= field["confidence"] <= 1.0, \
#             f"Field '{field_name}' confidence out of range: {field['confidence']}"


# @skip_if_missing
# def test_dates_are_iso_8601_when_present():
#     """Hard rule: dates are always ISO 8601 (YYYY-MM-DD), never MRZ raw YYMMDD."""
#     with open(CLEAN_PASSPORT, "rb") as f:
#         image_bytes = f.read()
#     result = run_ocr(image_bytes, "passport")
#     for date_field in ("dob", "expiry"):
#         if date_field in result["extracted_fields"]:
#             value = result["extracted_fields"][date_field]["value"]
#             assert ISO_DATE_PATTERN.match(value), f"{date_field} not ISO 8601: {value}"


# @skip_if_missing
# def test_mrz_raw_present_when_mrz_successfully_parsed():
#     with open(CLEAN_PASSPORT, "rb") as f:
#         image_bytes = f.read()
#     result = run_ocr(image_bytes, "passport")
#     if "mrz_raw" in result:
#         assert "line1" in result["mrz_raw"]
#         assert "line2" in result["mrz_raw"]
#         assert len(result["mrz_raw"]["line2"]) == 44, "TD3 line2 must be 44 chars"


"""
Unit tests for Module 1 - OCR Extraction.

Tests the real:
    backend.modules.module1_ocr.ocr_extraction.run_ocr

Test layers:
    1. Contract tests
       - No real image required.
       - Validate failure handling and response schema.

    2. Real-fixture tests
       - Parameterized across supported document types.
       - Fixtures are skipped automatically when missing.
       - Each document is tested with its correct doc_type.
       - Expected fields come from the document-type configuration.

Supported document types:
    - passport
    - visa
    - national_id
    - driving_license
    - permit
"""

import os
import re

import pytest

from backend.modules.module1_ocr.ocr_extraction import run_ocr


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FIXTURES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "fixtures")
)


# ---------------------------------------------------------------------------
# Test fixture configuration
#
# Add/remove fixture entries here without changing the test functions.
# ---------------------------------------------------------------------------

DOCUMENT_FIXTURES = [
    {
        "name": "synthetic_passport",
        "doc_type": "passport",
        "path": os.path.join(
            FIXTURES_DIR,
            "clean",
            "clean_passport_01.jpg",
        ),
        "expected_fields": {
            "name",
            "passport_number",
            "nationality",
            "dob",
            "expiry",
            "gender",
        },
        "date_fields": {"dob", "expiry"},
        "mrz": True,
    },
    {
        "name": "greek_passport_midv500",
        "doc_type": "passport",
        "path": os.path.join(
            FIXTURES_DIR,
            "clean",
            "25_grc_passport",
            "images",
            "CA",
            "CA25_01.jpg",
        ),
        "expected_fields": {
            "name",
            "passport_number",
            "nationality",
            "dob",
            "expiry",
            "gender",
        },
        "date_fields": {"dob", "expiry"},
        "mrz": True,
    },
    {
        "name": "finnish_driver_license_midv500",
        "doc_type": "driving_license",
        "path": os.path.join(
            FIXTURES_DIR,
            "clean",
            "23_fin_drvlic",
            "images",
            "CA",
            "CA23_01.jpg",
        ),
        "expected_fields": {
            "name",
            "license_number",
            "dob",
            "expiry",
        },
        "date_fields": {"dob", "expiry"},
        "mrz": False,
    },
    # data\fixtures\clean\24_fin_id\images\CA\CA24_01.jpg
    {
        "name": "national_id",
        "doc_type": "national_id",
        "path": os.path.join(
            FIXTURES_DIR,
            "clean",
            "24_fin_id",
            "images",
            "CA",
            "CA24_01.jpg",
        ),
        "expected_fields": {
            "name",
            "id_number",
            "dob",
        },
        "date_fields": {"dob"},
        "mrz": True,
    },

    # not testing for visa right now due to data insufficiency 
    # {
    #     "name": "visa",
    #     "doc_type": "visa",
    #     "path": os.path.join(
    #         FIXTURES_DIR,
    #         "clean",
    #         "visa",
    #         "visa_01.jpg",
    #     ),
    #     "expected_fields": {
    #         "visa_number",
    #         "visa_type",
    #         "entry_validation",
    #         "stay_duration",
    #     },
    #     "date_fields": set(),
    #     "mrz": False,
    # },

    # not doing testing for permit now due to data insufficiency
    # { 
    #     "name": "permit",
    #     "doc_type": "permit",
    #     "path": os.path.join(
    #         FIXTURES_DIR,
    #         "clean",
    #         "permit",
    #         "permit_01.jpg",
    #     ),
    #     "expected_fields": {
    #         "name",
    #         "permit_number",
    #         "validity",
    #     },
    #     "date_fields": set(),
    #     "mrz": False,
    # },
]


ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_fixture_bytes(path):
    """Read a fixture image as bytes."""
    with open(path, "rb") as f:
        return f.read()


def fixture_id(config):
    """Readable pytest ID."""
    return config["name"]


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------

def test_unknown_doc_type_fails_without_guessing():
    """
    Unknown document types must fail immediately.

    The OCR module must never guess an unsupported document type.
    """
    result = run_ocr(
        b"irrelevant bytes",
        "not_a_real_doc_type",
    )

    assert result["status"] == "failed"
    assert result["extracted_fields"] == {}


def test_garbage_bytes_never_raises():
    """
    Invalid image bytes must be handled gracefully.
    run_ocr() must not raise an exception.
    """
    result = run_ocr(
        b"this is not a valid jpeg",
        "passport",
    )

    assert result["status"] == "failed"
    assert result["extracted_fields"] == {}


def test_empty_bytes_never_raises():
    """
    Empty input must not raise an exception.
    """
    result = run_ocr(
        b"",
        "passport",
    )

    assert result["status"] in (
        "failed",
        "partial",
        "success",
    )


@pytest.mark.parametrize(
    "doc_type",
    [
        "passport",
        # "visa",
        "national_id",
        "driving_license",
        # "permit",
    ],
)
def test_supported_doc_types_return_valid_schema(doc_type):
    """
    Every configured document type must return the standard OCR schema,
    even when the input image is invalid.
    """
    result = run_ocr(
        b"invalid image bytes",
        doc_type,
    )

    assert isinstance(result, dict)

    for key in (
        "module",
        "doc_type",
        "status",
        "extracted_fields",
    ):
        assert key in result

    assert result["module"] == "ocr_extraction"
    assert result["doc_type"] == doc_type

    assert result["status"] in (
        "success",
        "partial",
        "failed",
    )

    assert isinstance(
        result["extracted_fields"],
        dict,
    )


# ---------------------------------------------------------------------------
# Real-fixture: basic OCR extraction
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "fixture",
    DOCUMENT_FIXTURES,
    ids=fixture_id,
)
def test_clean_document_returns_some_extracted_fields(fixture):
    """
    A valid clean document should produce at least one extracted field.

    Missing fixtures are skipped automatically.
    """
    path = fixture["path"]

    if not os.path.isfile(path):
        pytest.skip(
            f"Fixture not found: {path}"
        )

    image_bytes = load_fixture_bytes(path)

    result = run_ocr(
        image_bytes,
        fixture["doc_type"],
    )

    assert result["status"] in (
        "success",
        "partial",
    ), (
        f"{fixture['name']} returned "
        f"status='{result['status']}'"
    )

    assert result["extracted_fields"], (
        f"No fields extracted from "
        f"{fixture['name']}"
    )


# ---------------------------------------------------------------------------
# Real-fixture: field structure
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "fixture",
    DOCUMENT_FIXTURES,
    ids=fixture_id,
)
def test_every_extracted_field_has_valid_structure(fixture):
    """
    Every returned field must contain:
        value
        confidence

    Confidence must always be between 0 and 1.
    """
    path = fixture["path"]

    if not os.path.isfile(path):
        pytest.skip(
            f"Fixture not found: {path}"
        )

    image_bytes = load_fixture_bytes(path)

    result = run_ocr(
        image_bytes,
        fixture["doc_type"],
    )

    for field_name, field in result[
        "extracted_fields"
    ].items():

        assert isinstance(
            field,
            dict,
        ), (
            f"Field '{field_name}' must "
            f"be a dictionary"
        )

        assert "value" in field, (
            f"Field '{field_name}' "
            f"missing 'value'"
        )

        assert "confidence" in field, (
            f"Field '{field_name}' "
            f"missing 'confidence'"
        )

        assert field["value"] not in (
            None,
            "",
        ), (
            f"Field '{field_name}' "
            f"has empty value"
        )

        assert isinstance(
            field["confidence"],
            (int, float),
        ), (
            f"Field '{field_name}' "
            f"confidence must be numeric"
        )

        assert 0.0 <= field["confidence"] <= 1.0, (
            f"Field '{field_name}' "
            f"confidence out of range: "
            f"{field['confidence']}"
        )


# ---------------------------------------------------------------------------
# Real-fixture: expected document fields
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "fixture",
    DOCUMENT_FIXTURES,
    ids=fixture_id,
)
def test_extracted_fields_belong_to_document_schema(fixture):
    """
    OCR must not invent arbitrary field names.

    Returned fields must be part of the expected schema for
    that document type.
    """
    path = fixture["path"]

    if not os.path.isfile(path):
        pytest.skip(
            f"Fixture not found: {path}"
        )

    image_bytes = load_fixture_bytes(path)

    result = run_ocr(
        image_bytes,
        fixture["doc_type"],
    )

    expected_fields = fixture[
        "expected_fields"
    ]

    actual_fields = set(
        result["extracted_fields"].keys()
    )

    unexpected = actual_fields - expected_fields

    assert not unexpected, (
        f"{fixture['name']} returned "
        f"unexpected fields: {unexpected}"
    )


# ---------------------------------------------------------------------------
# Real-fixture: date validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "fixture",
    DOCUMENT_FIXTURES,
    ids=fixture_id,
)
def test_dates_are_iso_8601_when_present(fixture):
    """
    Date fields must use:
        YYYY-MM-DD

    This is especially important for MRZ-derived dates,
    which must not remain in YYMMDD format.
    """
    path = fixture["path"]

    if not os.path.isfile(path):
        pytest.skip(
            f"Fixture not found: {path}"
        )

    image_bytes = load_fixture_bytes(path)

    result = run_ocr(
        image_bytes,
        fixture["doc_type"],
    )

    for date_field in fixture["date_fields"]:

        if date_field not in result[
            "extracted_fields"
        ]:
            continue

        value = result[
            "extracted_fields"
        ][date_field]["value"]

        assert ISO_DATE_PATTERN.fullmatch(
            str(value)
        ), (
            f"{fixture['name']}: "
            f"{date_field} is not ISO 8601: "
            f"{value}"
        )


# ---------------------------------------------------------------------------
# Real-fixture: expected fields for successful/partial OCR
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "fixture",
    DOCUMENT_FIXTURES,
    ids=fixture_id,
)
def test_clean_document_extracts_at_least_one_expected_field(
    fixture,
):
    """
    A clean document must produce at least one field
    belonging to its configured schema.

    This intentionally does NOT require every field because
    OCR quality can vary by document image.
    """
    path = fixture["path"]

    if not os.path.isfile(path):
        pytest.skip(
            f"Fixture not found: {path}"
        )

    image_bytes = load_fixture_bytes(path)

    result = run_ocr(
        image_bytes,
        fixture["doc_type"],
    )

    actual_fields = set(
        result["extracted_fields"].keys()
    )

    expected_fields = fixture[
        "expected_fields"
    ]

    extracted_expected = (
        actual_fields & expected_fields
    )

    assert extracted_expected, (
        f"{fixture['name']} did not extract "
        f"any expected fields. "
        f"Got: {actual_fields}"
    )


# ---------------------------------------------------------------------------
# Real-fixture: MRZ validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "fixture",
    [
        fixture
        for fixture in DOCUMENT_FIXTURES
        if fixture["mrz"]
    ],
    ids=fixture_id,
)
def test_mrz_raw_is_valid_when_present(fixture):
    """
    Documents configured with MRZ support may return mrz_raw.

    When MRZ parsing succeeds:
        - line1 must exist
        - line2 must exist
        - TD3 line2 must contain 44 characters
    """
    path = fixture["path"]

    if not os.path.isfile(path):
        pytest.skip(
            f"Fixture not found: {path}"
        )

    image_bytes = load_fixture_bytes(path)

    result = run_ocr(
        image_bytes,
        fixture["doc_type"],
    )

    if "mrz_raw" not in result:
        return

    mrz_raw = result["mrz_raw"]

    assert isinstance(
        mrz_raw,
        dict,
    )

    assert "line1" in mrz_raw
    assert "line2" in mrz_raw

    assert len(
        mrz_raw["line1"]
    ) == 44, (
        f"{fixture['name']}: "
        f"TD3 line1 must contain 44 characters"
    )

    assert len(
        mrz_raw["line2"]
    ) == 44, (
        f"{fixture['name']}: "
        f"TD3 line2 must contain 44 characters"
    )


# ---------------------------------------------------------------------------
# Real-fixture: document-type correctness
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "fixture",
    DOCUMENT_FIXTURES,
    ids=fixture_id,
)
def test_result_preserves_document_type(fixture):
    """
    run_ocr() must return the same document type
    that the caller supplied.
    """
    path = fixture["path"]

    if not os.path.isfile(path):
        pytest.skip(
            f"Fixture not found: {path}"
        )

    image_bytes = load_fixture_bytes(path)

    result = run_ocr(
        image_bytes,
        fixture["doc_type"],
    )

    assert result["doc_type"] == fixture[
        "doc_type"
    ]
