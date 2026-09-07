"""
ocr_extraction.py — Module 1: OCR Extraction.

Converts document image bytes into structured field data.

Pipeline:
    image bytes
        -> OpenCV decode
        -> shared OCR preprocessing
        -> config-driven document type dispatch
        -> MRZ extraction when configured
        -> generic visual-zone OCR
        -> Section 9b output

OCR engines:
    1. EasyOCR — primary
    2. pytesseract — fallback

PaddleOCR is intentionally not used (see prior version's docstring for
the full explanation — paddlepaddle native dependency issue).

Hard rules:
    - run_ocr() accepts raw image bytes.
    - run_ocr() never raises for a bad image or OCR failure.
    - Every extracted field contains a 0.0-1.0 confidence.
    - Dates are normalized to YYYY-MM-DD.
    - Document layout comes from the shared document-type config.

*** THIS PASS — TWO CONFIRMED BUGS FIXED, evidence from real run on
    clean_passport_02.jpg (pasted output):
        {'gender': {'value': 'Date of Expiry: 2029-03-12', ...},
         'passport_number': {'value': 'REPUBLIC', ...}}

  BUG 1 — gender swallowed the NEXT field's full line.
    _extract_value_from_next_line()'s old `obvious_label_pattern` guard
    only rejected the next line if it was a BARE label with nothing else
    on it (fullmatch). Here the next OCR line was
    "Date of Expiry: 2029-03-12" — a label WITH its own value attached —
    which is not a bare label, so the guard let it through wholesale.
    FIX: new `_ANY_LABEL_START` regex now rejects the next line if it
    STARTS WITH any recognized field label, whether or not that label
    has its own value trailing it.

  BUG 2 — passport_number captured "REPUBLIC" (a passport-header word).
    Root cause: Section 3's format-based fallback grabs the first unused
    generic alphanumeric-looking token in the document for any field
    still missing, including passport_number. "REPUBLIC" (from
    "REPUBLIC OF INDIA" header text) matched the alphanumeric pattern
    with nothing to distinguish it from a real ID string.
    FIX: passport_number REMOVED from the alphanumeric fallback's
    candidate fields entirely. A wrong passport number silently corrupts
    Module 2 (checksum/DB lookup), Module 5 (authority match keyed off
    it), and Module 6 (declared_doc_number in the ledger) — worse than
    honestly returning status="partial" with the field missing. This
    field must come from MRZ or a same-line/next-line LABELED match
    only, never a blind format guess.

  MRZ DEBUG PRINTS added throughout extract_mrz() (Step 1 of the current
  investigation) — this fixture returned NO mrz_raw at all, meaning every
  one of the 5 fallback stages failed. These prints are temporary
  diagnostics; remove once the real failure point is identified and
  fixed, per the project's evidence-before-fix rule — do not guess at a
  fix without this output.
"""

from __future__ import annotations

import os
import re
import tempfile
from typing import List, Optional, Tuple

from .mrz_parser import ParsedMRZ, parse_mrz

# ---------------------------------------------------------------------------
# Optional OpenCV / NumPy
# ---------------------------------------------------------------------------

try:
    import cv2
    import numpy as np

    _HAS_CV2 = True
except ImportError:  # pragma: no cover
    cv2 = None
    np = None
    _HAS_CV2 = False


# ---------------------------------------------------------------------------
# Shared preprocessing
# ---------------------------------------------------------------------------

try:
    from ...preprocessing.image_preprocess import preprocess_for_ocr

    _HAS_SHARED_PREPROCESSING = True
except ImportError:  # pragma: no cover
    _HAS_SHARED_PREPROCESSING = False

    def preprocess_for_ocr(image):
        return image


# ---------------------------------------------------------------------------
# Shared document-type configuration
# ---------------------------------------------------------------------------

try:
    from ..shared.doc_types_config_loader import load_doc_types_config
except ImportError:  # pragma: no cover

    def load_doc_types_config():
        return {}


# ---------------------------------------------------------------------------
# OCR engine
# ---------------------------------------------------------------------------

_OCR_ENGINE = None
_OCR_BACKEND = None

try:
    import easyocr

    _OCR_ENGINE = easyocr.Reader(["en"], gpu=False)
    _OCR_BACKEND = "easyocr"

except Exception:
    try:
        import pytesseract

        _OCR_ENGINE = pytesseract
        _OCR_BACKEND = "pytesseract"

    except Exception:
        _OCR_ENGINE = None
        _OCR_BACKEND = None


# ---------------------------------------------------------------------------
# Optional PassportEye
# ---------------------------------------------------------------------------

try:
    from passporteye import read_mrz as _passporteye_read_mrz

    _HAS_PASSPORTEYE = True
except Exception:  # pragma: no cover
    _HAS_PASSPORTEYE = False


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MRZ_LINE_PATTERN = re.compile(r"^[A-Z0-9<]{20,44}$")

# Confirmed bug (real fixtures): EasyOCR misreads digit '0' as letter
# 'O' specifically right after "IND" in TD3 line 2 — e.g.
# "IND0308153" -> "INDO308153" — breaking checksum math on genuinely
# CLEAN documents whenever the DOB/expiry year starts with '0'.
# Fixed here rather than in document_validation.py: this is an OCR
# read error at the source, not a validation-logic problem, and
# checksum.py's math is independently confirmed correct by hand.
_OCR_DIGIT_CONFUSIONS = {
    "O": "0",
    "I": "1",
    "L": "1",
    "S": "5",
    "B": "8",
    "Z": "2",
}

# TD3 line 2 fixed-width positions that are numeric-only per ICAO 9303 —
# safe to correct, unlike free-text zones (name, personal_number) where
# a letter could be genuinely intended.
_TD3_LINE2_NUMERIC_POSITIONS = [9] + list(range(13, 20)) + list(range(21, 28)) + [42, 43]


def _fix_td3_line2_numeric_confusions(line2: str) -> str:
    """Correct OCR letter/digit confusions ONLY at TD3 line 2's known
    numeric-only positions (doc_number_check, dob+check, expiry+check,
    personal_number_check, composite_check). Never touches doc_number,
    nationality, sex, or personal_number zones, which can legitimately
    contain letters."""
    if not line2 or len(line2) != 44:
        return line2

    chars = list(line2)
    for idx in _TD3_LINE2_NUMERIC_POSITIONS:
        ch = chars[idx]
        if ch in _OCR_DIGIT_CONFUSIONS:
            chars[idx] = _OCR_DIGIT_CONFUSIONS[ch]
    return "".join(chars)

_DATE_FIELDS = {"dob", "expiry", "validity"}

# Every pattern follows:
#
#     label
#     whitespace
#     optional separator
#     whitespace
#     captured value
#
# Keep this structure because the next-line label fallback depends on it.

_LABEL_PATTERNS = {
    "name": (
        r"(?:name|surname|full\s+name)"
        r"\s*[:=\-]?\s*"
        r"([A-Z][A-Z\s,.'-]{2,40})"
    ),

    "passport_number": (
        r"(?:passport\s*(?:no\.?|number)?)"
        r"\s*[:=\-]?\s*"
        r"([A-Z0-9]{6,10})"
    ),

    "dob": (
        r"(?:dob|date\s+of\s+birth|birth)"
        r"\s*[:=\-]?\s*"
        r"("
        r"\d{4}[\/\-.]\d{1,2}[\/\-.]\d{1,2}"
        r"|"
        r"\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}"
        r")"
    ),

    "expiry": (
        r"(?:expiry|expires?|valid\s+(?:until|thru))"
        r"\s*[:=\-]?\s*"
        r"("
        r"\d{4}[\/\-.]\d{1,2}[\/\-.]\d{1,2}"
        r"|"
        r"\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}"
        r")"
    ),

    "license_number": (
        r"(?:licen[cs]e\s*(?:no\.?|number)?)"
        r"\s*[:=\-]?\s*"
        r"([A-Z0-9\-]{5,20})"
    ),

    "id_number": (
        r"(?:id\s*(?:no\.?|number)?)"
        r"\s*[:=\-]?\s*"
        r"([A-Z0-9\-]{5,20})"
    ),

    "permit_number": (
        r"(?:permit\s*(?:no\.?|number)?)"
        r"\s*[:=\-]?\s*"
        r"([A-Z0-9\-]{5,20})"
    ),

    "visa_number": (
        r"(?:visa\s*(?:no\.?|number)?)"
        r"\s*[:=\-]?\s*"
        r"([A-Z0-9\-]{5,20})"
    ),

    "visa_type": (
        r"(?:visa\s+type|type)"
        r"\s*[:=\-]?\s*"
        r"([A-Z0-9]{1,15})"
    ),

    "entry_validation": (
        r"(?:entry\s+validation)"
        r"\s*[:=\-]?\s*"
        r"([A-Z0-9\/.\- ]{1,20})"
    ),

    "stay_duration": (
        r"(?:stay|duration)"
        r"\s*[:=\-]?\s*"
        r"(\d{1,4}\s*(?:days|months|years))"
    ),

    "nationality": (
        r"(?:nationality)"
        r"\s*[:=\-]?\s*"
        r"([A-Z]{2,20})"
    ),

    "gender": (
        r"(?:sex|gender)"
        r"\s*[:=\-]?\s*"
        r"([MF])"
    ),

    "validity": (
        r"(?:valid(?:ity)?)"
        r"\s*[:=\-]?\s*"
        r"("
        r"\d{4}[\/\-.]\d{1,2}[\/\-.]\d{1,2}"
        r"|"
        r"\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}"
        r")"
    ),
}

_LABEL_TEMPLATE_SPLIT = r"\s*[:=\-]?\s*"

# NEW — matches this pass's Bug 1 fix. Any recognized field label,
# whether it appears bare ("Sex:") or WITH its own value attached
# ("Date of Expiry: 2029-03-12"). Used to reject a "next line" candidate
# for the label-on-one-line/value-on-next-line fallback if that next
# line is actually itself the start of a different field, not a value.
_ANY_LABEL_START = re.compile(
    r"^\s*(?:"
    r"sex|gender|"
    r"date\s+of\s+birth|dob|birth|"
    r"date\s+of\s+expiry|expiry|expires?|valid\s+(?:until|thru)|"
    r"nationality|"
    r"surname|given\s+name(?:s)?|full\s+name|name|"
    r"passport(?:\s+no\.?|\s+number)?|"
    r"type|authority|"
    r"place\s+of\s+(?:birth|issue)|"
    r"licen[cs]e(?:\s+no\.?|\s+number)?|"
    r"id(?:\s+no\.?|\s+number)?|"
    r"permit(?:\s+no\.?|\s+number)?|"
    r"visa(?:\s+no\.?|\s+number|\s+type)?|"
    r"entry\s+validation|"
    r"stay|duration|"
    r"valid(?:ity)?"
    r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _safe_confidence(value: float, minimum: float = 0.30) -> float:
    """Return a confidence guaranteed to be within 0.0-1.0."""

    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.5

    return round(min(max(value, minimum), 0.97), 2)


def _normalize_date(raw: str) -> Optional[str]:
    """
    Convert common date formats to ISO YYYY-MM-DD.

    Supported:
        YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
        DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
        DD-MM-YY, DD/MM/YY, DD.MM.YY
    """

    if not raw:
        return None

    raw = str(raw).strip()

    for separator in ("/", "-", "."):
        if separator not in raw:
            continue

        parts = raw.split(separator)

        if len(parts) != 3:
            continue

        a, b, c = parts

        try:
            if len(a) == 4:
                year = int(a)
                month = int(b)
                day = int(c)
            else:
                day = int(a)
                month = int(b)
                year = int(c)

                if len(str(c)) == 2:
                    year = 2000 + year if year <= 30 else 1900 + year

            if not 1 <= month <= 12:
                return None

            if not 1 <= day <= 31:
                return None

            if not 1900 <= year <= 2100:
                return None

            return f"{year:04d}-{month:02d}-{day:02d}"

        except (TypeError, ValueError):
            return None

    return None


def _clean_ocr_text(text: str) -> str:
    """Normalize OCR text without destroying MRZ '<' characters."""

    return re.sub(r"\s+", " ", str(text)).strip()


# ---------------------------------------------------------------------------
# Basic OCR
# ---------------------------------------------------------------------------

def _ocr_text_lines(image) -> List[str]:
    """
    Run the available OCR backend and return recognized text lines.

    Best effort: failure -> [].
    """

    if image is None or _OCR_ENGINE is None:
        return []

    try:

        if _OCR_BACKEND == "easyocr":
            result = _OCR_ENGINE.readtext(
                image,
                detail=0,
                paragraph=False,
            )

            return [
                str(line).strip()
                for line in result
                if str(line).strip()
            ]

        if _OCR_BACKEND == "pytesseract":
            text = _OCR_ENGINE.image_to_string(image)

            return [
                line.strip()
                for line in text.splitlines()
                if line.strip()
            ]

    except Exception:
        return []

    return []


# ---------------------------------------------------------------------------
# MRZ OCR reconstruction
# ---------------------------------------------------------------------------

def _extract_mrz_band_lines(band_image) -> List[str]:
    """
    OCR an MRZ crop and reconstruct logical lines.

    EasyOCR can split one MRZ line into multiple bounding boxes.
    Bounding boxes are clustered by Y position and joined left-to-right.
    """

    if band_image is None or _OCR_ENGINE is None:
        return []

    if _OCR_BACKEND == "easyocr":

        try:
            detections = _OCR_ENGINE.readtext(
                band_image,
                detail=1,
                paragraph=False,
            )
        except Exception:
            return []

        if not detections:
            return []

        rows = []

        for item in detections:

            if len(item) != 3:
                continue

            bbox, text, confidence = item

            text = str(text).strip()

            if not text:
                continue

            try:
                xs = [float(point[0]) for point in bbox]
                ys = [float(point[1]) for point in bbox]
            except Exception:
                continue

            x_left = min(xs)
            y_center = sum(ys) / len(ys)

            box_height = max(ys) - min(ys)

            tolerance = max(12.0, box_height * 0.65)

            placed = False

            for row in rows:

                if abs(row["y"] - y_center) <= tolerance:

                    # FIX: "y" key must be stored on the fragment itself
                    # (this was the bug — fragments only had x/text/
                    # confidence, so recomputing the row average below
                    # by reading item["y"] raised KeyError: 'y' the
                    # moment 2+ fragments landed in the same row).
                    row["fragments"].append(
                        {
                            "x": x_left,
                            "y": y_center,
                            "text": text,
                            "confidence": float(confidence),
                        }
                    )

                    row["y"] = (
                        sum(item["y"] for item in row["fragments"])
                        / len(row["fragments"])
                    )

                    placed = True
                    break

            if not placed:
                rows.append(
                    {
                        "y": y_center,
                        "fragments": [
                            {
                                "x": x_left,
                                "y": y_center,
                                "text": text,
                                "confidence": float(confidence),
                            }
                        ],
                    }
                )

        rows.sort(key=lambda row: row["y"])

        output = []

        for row in rows:

            fragments = sorted(row["fragments"], key=lambda item: item["x"])

            reconstructed = "".join(fragment["text"] for fragment in fragments)

            reconstructed = re.sub(r"[^A-Z0-9<]", "", reconstructed.upper())

            if reconstructed:
                output.append(reconstructed)

        return output

    # pytesseract fallback
    return [
        re.sub(r"[^A-Z0-9<]", "", line.upper())
        for line in _ocr_text_lines(band_image)
        if line.strip()
    ]


def _mrz_confidence_from_backend(image) -> float:
    """Best-effort OCR confidence for an MRZ crop."""

    if image is None or _OCR_ENGINE is None:
        return 0.5

    try:

        if _OCR_BACKEND == "easyocr":

            result = _OCR_ENGINE.readtext(
                image,
                detail=1,
                paragraph=False,
            )

            scores = [float(item[2]) for item in result if len(item) == 3]

            if scores:
                return _safe_confidence(sum(scores) / len(scores))

    except Exception:
        pass

    return 0.60


# ---------------------------------------------------------------------------
# PassportEye MRZ extraction
# ---------------------------------------------------------------------------

def _extract_mrz_with_passporteye(
    image,
    mrz_format: str,
) -> Tuple[Optional[ParsedMRZ], float]:

    if (
        not _HAS_PASSPORTEYE
        or not _HAS_CV2
        or image is None
        or mrz_format not in ("TD3", "TD3_or_none")
    ):
        print(f"DEBUG MRZ [passporteye]: skipped — has_passporteye={_HAS_PASSPORTEYE}, "
              f"has_cv2={_HAS_CV2}, image_none={image is None}, mrz_format={mrz_format}")
        return None, 0.0

    temp_path = None

    try:

        fd, temp_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)

        if not cv2.imwrite(temp_path, image):
            print("DEBUG MRZ [passporteye]: cv2.imwrite failed")
            return None, 0.0

        mrz_result = _passporteye_read_mrz(temp_path)

        if not mrz_result:
            print("DEBUG MRZ [passporteye]: read_mrz() returned falsy — no MRZ zone located")
            return None, 0.0

        raw = {}

        try:
            raw = mrz_result.to_dict()
        except Exception as e:
            print(f"DEBUG MRZ [passporteye]: to_dict() failed: {e}")
            raw = {}

        print(f"DEBUG MRZ [passporteye]: raw dict keys = {list(raw.keys())}")

        raw_lines = []

        for key in ("raw_text", "raw_mrz", "mrz"):

            value = raw.get(key)

            if isinstance(value, str):

                raw_lines = [line.strip() for line in value.splitlines() if line.strip()]

                if raw_lines:
                    break

        print(f"DEBUG MRZ [passporteye]: raw_lines found = {raw_lines}")

        if len(raw_lines) < 2:
            print("DEBUG MRZ [passporteye]: fewer than 2 raw lines — cannot parse TD3")
            return None, 0.0

        candidate_lines = [
            re.sub(r"[^A-Z0-9<]", "", line.upper())
            for line in raw_lines[:2]
        ]

        print(f"DEBUG MRZ [passporteye]: candidate_lines = {candidate_lines}, "
              f"lengths = {[len(l) for l in candidate_lines]}")

        parsed = parse_mrz(candidate_lines, mrz_format)

        if parsed is None:
            print("DEBUG MRZ [passporteye]: parse_mrz() returned None")
            return None, 0.0

        print("DEBUG MRZ [passporteye]: SUCCESS")
        return parsed, 0.90

    except Exception as e:
        print(f"DEBUG MRZ [passporteye]: exception: {e}")
        return None, 0.0

    finally:

        if temp_path:

            try:
                os.remove(temp_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# MRZ extraction
# ---------------------------------------------------------------------------

def extract_mrz(
    image,
    mrz_format: str,
) -> Tuple[Optional[ParsedMRZ], float]:
    """
    Locate and parse an MRZ.

    Strategy:
        1. PassportEye for TD3 when available.
        2. EasyOCR full-frame MRZ detection.
        3. Localized MRZ crop + reconstructed OCR.
        4. Full-frame detection fallback.
        5. Bottom-band fallback.

    Returns:
        (ParsedMRZ | None, confidence)

    TEMPORARY: DEBUG prints added at every fallback stage per the
    project's evidence-before-fix rule — this fixture returned NO
    mrz_raw at all in the last full pipeline run, so we need to see
    exactly which stage(s) failed and why before changing any logic.
    Remove these prints once the real failure point is fixed.
    """

    if image is None or not mrz_format or mrz_format.lower() == "none":
        print(f"DEBUG MRZ: extract_mrz called with image_none={image is None}, "
              f"mrz_format={mrz_format} — returning immediately")
        return None, 0.0

    # ------------------------------------------------------------------
    # 1. PassportEye
    # ------------------------------------------------------------------

    parsed, confidence = _extract_mrz_with_passporteye(image, mrz_format)

    if parsed is not None:
        return parsed, confidence

    # ------------------------------------------------------------------
    # 2. EasyOCR full-frame localization
    # ------------------------------------------------------------------

    if _OCR_BACKEND == "easyocr" and _OCR_ENGINE is not None:

        try:

            detections = _OCR_ENGINE.readtext(image, detail=1, paragraph=False)

            mrz_detections = []

            for item in detections:

                if len(item) != 3:
                    continue

                bbox, text, confidence = item

                cleaned = re.sub(r"[^A-Z0-9<]", "", str(text).upper())

                if len(cleaned) < 8:
                    continue

                # FIX: dropped the "or starts with P" branch — it wrongly
                # matched "PASSPORT" (document title) and "PASSPORTNO"
                # (a label), inflating the MRZ bounding box across most
                # of the page. Real MRZ fragments always contain '<'.
                looks_like_mrz = "<" in cleaned

                if not looks_like_mrz:
                    continue

                xs = [float(point[0]) for point in bbox]
                ys = [float(point[1]) for point in bbox]

                mrz_detections.append(
                    {
                        "bbox": (min(xs), min(ys), max(xs), max(ys)),
                        "text": cleaned,
                        "confidence": float(confidence),
                    }
                )

            print(f"DEBUG MRZ [easyocr full-frame]: mrz_detections found = {mrz_detections}")

            if mrz_detections:

                # ------------------------------------------------------
                # 3. Localized crop
                # ------------------------------------------------------

                x1 = min(item["bbox"][0] for item in mrz_detections)
                y1 = min(item["bbox"][1] for item in mrz_detections)
                x2 = max(item["bbox"][2] for item in mrz_detections)
                y2 = max(item["bbox"][3] for item in mrz_detections)

                height, width = image.shape[:2]

                box_width = max(x2 - x1, 1)
                box_height = max(y2 - y1, 1)

                pad_x = int(box_width * 0.08)
                pad_y = int(box_height * 0.50)

                crop_x1 = max(0, int(x1 - pad_x))
                crop_y1 = max(0, int(y1 - pad_y))
                crop_x2 = min(width, int(x2 + pad_x))
                crop_y2 = min(height, int(y2 + pad_y))

                mrz_crop = image[crop_y1:crop_y2, crop_x1:crop_x2]

                # ------------------------------------------------------
                # 4. Re-run OCR on localized crop
                # ------------------------------------------------------

                raw_lines = _extract_mrz_band_lines(mrz_crop)

                candidate_lines = [
                    re.sub(r"[^A-Z0-9<]", "", line.upper()) for line in raw_lines
                ]

                # PAD FIX: EasyOCR can drop a run of trailing '<' filler
                # characters (confirmed — a genuine 44-char TD3 line came
                # back as 36 chars with an OCR detection gap in the
                # filler run). Trailing '<' carries no semantic content,
                # so right-padding up to 44 is safe and loses nothing —
                # unlike padding in the middle of a line, which would
                # risk corrupting real data.
                if mrz_format in ("TD3", "TD3_or_none"):
                    candidate_lines = [
                        line.ljust(44, "<") if 30 <= len(line) < 44 else line
                        for line in candidate_lines
                    ]

                candidate_lines = [
                    line for line in candidate_lines if _MRZ_LINE_PATTERN.match(line)
                ]

                if mrz_format in ("TD3", "TD3_or_none"):
                    candidate_lines = [
                        line[:44] for line in candidate_lines if len(line) >= 44
                    ]

                # Fix confirmed OCR '0'/'O' confusion on line 2's numeric
                # positions before checksum-sensitive parsing.
                if mrz_format in ("TD3", "TD3_or_none") and len(candidate_lines) >= 2:
                    candidate_lines[1] = _fix_td3_line2_numeric_confusions(candidate_lines[1])

                print(f"DEBUG MRZ [localized crop]: raw_lines = {raw_lines}")
                print(f"DEBUG MRZ [localized crop]: candidate_lines (post-filter) = {candidate_lines}")

                parsed = parse_mrz(candidate_lines, mrz_format)

                if parsed is not None:
                    confidence = _mrz_confidence_from_backend(mrz_crop)
                    print("DEBUG MRZ [localized crop]: SUCCESS")
                    return parsed, confidence

                print("DEBUG MRZ [localized crop]: parse_mrz() returned None")

                # ------------------------------------------------------
                # 5. Try full-frame detections directly
                # ------------------------------------------------------

                detected_lines = [
                    item["text"]
                    for item in sorted(
                        mrz_detections, key=lambda item: (item["bbox"][1], item["bbox"][0])
                    )
                ]

                if mrz_format in ("TD3", "TD3_or_none"):
                    detected_lines = [
                        line.ljust(44, "<") if 30 <= len(line) < 44 else line
                        for line in detected_lines
                    ]

                detected_lines = [
                    line for line in detected_lines if _MRZ_LINE_PATTERN.match(line)
                ]

                if mrz_format in ("TD3", "TD3_or_none"):
                    detected_lines = [
                        line[:44] for line in detected_lines if len(line) >= 44
                    ]

                if mrz_format in ("TD3", "TD3_or_none") and len(detected_lines) >= 2:
                    detected_lines[1] = _fix_td3_line2_numeric_confusions(detected_lines[1])

                print(f"DEBUG MRZ [full-frame direct]: detected_lines (post-filter) = {detected_lines}")

                parsed = parse_mrz(detected_lines, mrz_format)

                if parsed is not None:
                    confidences = [item["confidence"] for item in mrz_detections]
                    confidence = sum(confidences) / len(confidences) if confidences else 0.50
                    print("DEBUG MRZ [full-frame direct]: SUCCESS")
                    return parsed, _safe_confidence(confidence)

                print("DEBUG MRZ [full-frame direct]: parse_mrz() returned None")
            else:
                print("DEBUG MRZ [easyocr full-frame]: no MRZ-like detections in whole image")

        except Exception as e:
            print(f"DEBUG MRZ [easyocr full-frame]: exception: {e}")

    else:
        print(f"DEBUG MRZ [easyocr full-frame]: skipped — backend={_OCR_BACKEND}")

    # ------------------------------------------------------------------
    # 6. Final bottom-band fallback
    # ------------------------------------------------------------------

    if not _HAS_CV2:
        print("DEBUG MRZ [bottom-band]: skipped — no cv2")
        return None, 0.0

    try:

        height, width = image.shape[:2]

        band = image[int(height * 0.60):height, 0:width]

        raw_lines = _extract_mrz_band_lines(band)

        candidate_lines = [
            re.sub(r"[^A-Z0-9<]", "", line.upper()) for line in raw_lines
        ]

        if mrz_format in ("TD3", "TD3_or_none"):
            candidate_lines = [
                line.ljust(44, "<") if 30 <= len(line) < 44 else line
                for line in candidate_lines
            ]

        candidate_lines = [
            line for line in candidate_lines if _MRZ_LINE_PATTERN.match(line)
        ]

        if mrz_format in ("TD3", "TD3_or_none"):
            candidate_lines = [
                line[:44] for line in candidate_lines if len(line) >= 44
            ]

        if mrz_format in ("TD3", "TD3_or_none") and len(candidate_lines) >= 2:
            candidate_lines[1] = _fix_td3_line2_numeric_confusions(candidate_lines[1])

        print(f"DEBUG MRZ [bottom-band]: raw_lines = {raw_lines}")
        print(f"DEBUG MRZ [bottom-band]: candidate_lines (post-filter) = {candidate_lines}")

        parsed = parse_mrz(candidate_lines, mrz_format)

        if parsed is not None:
            confidence = _mrz_confidence_from_backend(band)
            print("DEBUG MRZ [bottom-band]: SUCCESS")
            return parsed, confidence

        print("DEBUG MRZ [bottom-band]: parse_mrz() returned None — ALL MRZ STRATEGIES EXHAUSTED")

    except Exception as e:
        print(f"DEBUG MRZ [bottom-band]: exception: {e}")

    return None, 0.0


# ---------------------------------------------------------------------------
# Generic visual-zone OCR
# ---------------------------------------------------------------------------

def _get_ocr_detections(image) -> list:
    """Return OCR detections with spatial metadata."""

    detections = []

    if _OCR_BACKEND == "easyocr" and _OCR_ENGINE is not None:

        try:

            raw = _OCR_ENGINE.readtext(
                image,
                detail=1,
                paragraph=False,
                mag_ratio=1.5,
            )

            for item in raw:

                if len(item) != 3:
                    continue

                bbox, text, confidence = item

                text = str(text).strip()

                if not text:
                    continue

                xs = [float(point[0]) for point in bbox]
                ys = [float(point[1]) for point in bbox]

                detections.append(
                    {
                        "text": text,
                        "confidence": float(confidence),
                        "x1": min(xs),
                        "y1": min(ys),
                        "x2": max(xs),
                        "y2": max(ys),
                        "cx": sum(xs) / len(xs),
                        "cy": sum(ys) / len(ys),
                    }
                )

        except Exception:
            detections = []

    if not detections:

        lines = _ocr_text_lines(image)

        for text in lines:

            text = str(text).strip()

            if not text:
                continue

            detections.append(
                {
                    "text": text,
                    "confidence": 0.50,
                    "x1": 0,
                    "y1": 0,
                    "x2": 0,
                    "y2": 0,
                    "cx": 0,
                    "cy": 0,
                }
            )

    return detections


def _group_ocr_rows(detections: list) -> list:
    """Group OCR detections into visual rows."""

    if not detections:
        return []

    detections = sorted(detections, key=lambda item: (item["cy"], item["cx"]))

    rows = []

    for detection in detections:

        box_height = max(detection["y2"] - detection["y1"], 1)

        tolerance = max(12, box_height * 0.65)

        placed = False

        for row in rows:

            if abs(detection["cy"] - row["cy"]) <= tolerance:

                row["items"].append(detection)

                row["cy"] = sum(item["cy"] for item in row["items"]) / len(row["items"])

                placed = True
                break

        if not placed:

            rows.append({"cy": detection["cy"], "items": [detection]})

    rows.sort(key=lambda row: row["cy"])

    return rows


def _reconstruct_rows(rows: list) -> list:
    """Convert grouped OCR detections into text lines."""

    reconstructed = []

    for row in rows:

        items = sorted(row["items"], key=lambda item: item["cx"])

        text = " ".join(item["text"] for item in items).strip()

        confidences = [item["confidence"] for item in items]

        confidence = sum(confidences) / len(confidences) if confidences else 0.50

        reconstructed.append({"text": text, "confidence": confidence, "items": items})

    return reconstructed


def _extract_value_from_next_line(
    current_line: str,
    next_line: str,
    pattern: str,
) -> Optional[str]:
    """
    Extract a value when the layout is:

        LABEL:
        VALUE

    FIX (this pass): the old guard only rejected `next_line` if it was
    an exact, bare label with nothing else on it. That let a next_line
    like "Date of Expiry: 2029-03-12" through untouched, since it isn't
    a BARE label — it's a label WITH its own value. Now uses
    `_ANY_LABEL_START`, which rejects next_line if it starts with ANY
    recognized field label, attached value or not. This is the fix for
    the confirmed 'gender' bug (captured the whole next field's line).
    """

    try:
        label_part = pattern.split(r"\s*[:=\-]?\s*", 1)[0]

        label_regex = re.compile(
            rf"^\s*{label_part}\s*[:=\-]?\s*$",
            re.IGNORECASE,
        )

        if not label_regex.fullmatch(current_line.strip()):
            return None

        value = next_line.strip()

        if not value:
            return None

        # NEW GUARD — reject if next_line is itself the start of ANY
        # other recognized field (with or without its own value attached).
        if _ANY_LABEL_START.match(value):
            return None

        return value

    except Exception:
        return None


def _format_based_candidates(reconstructed_lines: list) -> dict:
    """
    Find date and document-number candidates.

    Used only when label-based OCR fails.
    """

    result = {"dates": [], "alphanumeric": []}

    for line in reconstructed_lines:

        text = line["text"]

        date_matches = re.findall(
            r"\b\d{4}[./-]\d{1,2}[./-]\d{1,2}\b"
            r"|"
            r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",
            text,
        )

        for value in date_matches:

            normalized = _normalize_date(value)

            if normalized:

                result["dates"].append(
                    {"value": normalized, "confidence": line["confidence"]}
                )

        candidates = re.findall(
            r"\b[A-Z0-9][A-Z0-9\-]{5,19}\b",
            text.upper(),
        )

        for value in candidates:

            result["alphanumeric"].append(
                {"value": value, "confidence": line["confidence"]}
            )

    return result


def extract_generic_fields(image, expected_fields) -> dict:
    """
    Extract non-MRZ fields using OCR text lines.

    Extraction order:
        1. Same-line label/value.
        2. Label on one line + value on next line.
        3. Format-based fallback for dates/document numbers.

    FIX (this pass): passport_number is EXCLUDED from step 3's
    alphanumeric fallback (see `number_fields` below). Confirmed bug:
    the fallback grabbed "REPUBLIC" (from a passport's header text) as
    passport_number, since the generic alphanumeric pattern has no way
    to distinguish header/boilerplate words from a real document number.
    A wrong identifier silently corrupts every downstream module keyed
    off it (Module 2 checksum/DB lookup, Module 5 authority match,
    Module 6 ledger) — a missing field (status="partial") is safer and
    more honest than a confidently wrong one here. passport_number must
    now come from MRZ or a genuine labeled (same-line / next-line) OCR
    match only.

    Returns:
        {field: {"value": ..., "confidence": 0.0-1.0}}
    """

    if image is None or not expected_fields:
        return {}

    detections = _get_ocr_detections(image)

    if not detections:
        return {}

    rows = _group_ocr_rows(detections)

    reconstructed_lines = _reconstruct_rows(rows)

    if not reconstructed_lines:
        return {}

    extracted = {}

    # ------------------------------------------------------------------
    # 1. Same-line label/value extraction
    # ------------------------------------------------------------------

    for field in expected_fields:

        pattern = _LABEL_PATTERNS.get(field)

        if not pattern:
            continue

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            continue

        for line in reconstructed_lines:

            match = regex.search(line["text"])

            if not match:
                continue

            value = match.group(1).strip()

            if not value:
                continue

            if field in _DATE_FIELDS:

                value = _normalize_date(value)

                if not value:
                    continue

            extracted[field] = {
                "value": value,
                "confidence": _safe_confidence(line["confidence"]),
            }

            break

    # ------------------------------------------------------------------
    # 2. Label on current line, value on next line
    # ------------------------------------------------------------------

    for index in range(len(reconstructed_lines) - 1):

        current_line = reconstructed_lines[index]["text"].strip()

        next_line = reconstructed_lines[index + 1]["text"].strip()

        if not current_line or not next_line:
            continue

        for field in expected_fields:

            if field in extracted:
                continue

            pattern = _LABEL_PATTERNS.get(field)

            if not pattern:
                continue

            value = _extract_value_from_next_line(current_line, next_line, pattern)

            if not value:
                continue

            if field in _DATE_FIELDS:

                value = _normalize_date(value)

                if not value:
                    continue

            extracted[field] = {
                "value": value,
                "confidence": _safe_confidence(
                    reconstructed_lines[index + 1]["confidence"]
                ),
            }

    # ------------------------------------------------------------------
    # 3. Format-based fallback
    # ------------------------------------------------------------------

    missing_fields = [field for field in expected_fields if field not in extracted]

    if missing_fields:

        candidates = _format_based_candidates(reconstructed_lines)

        # Dates
        date_fields = [field for field in missing_fields if field in _DATE_FIELDS]

        unused_dates = list(candidates["dates"])

        for field in date_fields:

            if not unused_dates:
                break

            candidate = unused_dates.pop(0)

            extracted[field] = {
                "value": candidate["value"],
                "confidence": _safe_confidence(candidate["confidence"]),
            }

        # Document numbers — passport_number DELIBERATELY EXCLUDED, see
        # this function's docstring for why.
        number_fields = [
            field
            for field in missing_fields
            if field in {"license_number", "id_number", "permit_number", "visa_number"}
        ]

        unused_numbers = list(candidates["alphanumeric"])

        for field in number_fields:

            if field in extracted:
                continue

            if not unused_numbers:
                break

            candidate = unused_numbers.pop(0)

            extracted[field] = {
                "value": candidate["value"],
                "confidence": _safe_confidence(candidate["confidence"] * 0.85),
            }

    return extracted


# ---------------------------------------------------------------------------
# Top-level Module 1 dispatcher
# ---------------------------------------------------------------------------

def run_ocr(
    doc_image_bytes: bytes,
    doc_type: str,
    config: Optional[dict] = None,
) -> dict:
    """
    Convert document image bytes into the Module 1 output contract.

    Never raises. Failure output:
        {"module": "ocr_extraction", "doc_type": "...",
         "status": "failed", "extracted_fields": {}}
    """

    result = {
        "module": "ocr_extraction",
        "doc_type": doc_type,
        "status": "failed",
        "extracted_fields": {},
    }

    try:

        cfg = config if config is not None else load_doc_types_config()

        if not isinstance(cfg, dict):
            return result

        doc_cfg = cfg.get(doc_type)

        if not isinstance(doc_cfg, dict):
            return result

        expected_fields = doc_cfg.get("expected_fields", [])

        if not isinstance(expected_fields, list):
            expected_fields = []

        mrz_format = doc_cfg.get("mrz_format", "none")

        if (
            not _HAS_CV2
            or not doc_image_bytes
            or not isinstance(doc_image_bytes, (bytes, bytearray))
        ):
            return result

        arr = np.frombuffer(doc_image_bytes, dtype=np.uint8)

        image = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if image is None:
            return result

        try:
            image = preprocess_for_ocr(image)
        except Exception:
            pass

        if image is None:
            return result
        
        extracted = {}

        mrz_raw = None
        generic_fields = extract_generic_fields(image, expected_fields)

        if mrz_format and str(mrz_format).lower() != "none":
            parsed_mrz, mrz_confidence = extract_mrz(image, mrz_format)

            if parsed_mrz is not None:
                try:
                    mrz_raw = parsed_mrz.as_raw_dict()
                except Exception:
                    mrz_raw = None

                for field in expected_fields:
                    mrz_field = parsed_mrz.fields.get(field)

                    if mrz_field is not None and mrz_field.value:
                        value = mrz_field.value

                        if field in _DATE_FIELDS:
                            normalized = _normalize_date(value)

                            if normalized:
                                value = normalized
                            else:
                                continue

                        visual_field = generic_fields.get(field)

                        if visual_field is not None:
                            confidence = visual_field["confidence"]
                        else:
                            confidence = _safe_confidence(mrz_confidence)

                        extracted[field] = {
                            "value": value,
                            "confidence": _safe_confidence(confidence),
                        }

        missing_fields = [
            field for field in expected_fields
            if field not in extracted
        ]

        if missing_fields:
            for field in missing_fields:
                if field in generic_fields:
                    extracted[field] = generic_fields[field]

        result["extracted_fields"] = extracted

        if mrz_raw is not None:
            result["mrz_raw"] = mrz_raw

        found = len(extracted)

        total = len(expected_fields) if expected_fields else 1

        if found == 0:
            result["status"] = "failed"
        elif found < total:
            result["status"] = "partial"
        else:
            result["status"] = "success"

        return result

    except Exception:

        result["status"] = "failed"
        result["extracted_fields"] = {}

        return result


# ---------------------------------------------------------------------------
# Manual execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    image_path = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..",
        "data", "fixtures", "clean",
        "clean_passport_02.jpg",
    )

    try:

        with open(image_path, "rb") as file:
            image_bytes = file.read()

        print(run_ocr(image_bytes, "passport"))

    except Exception as exc:

        print(f"Manual OCR test failed: {exc}")