
/













Ocr extraction · PY
"""
ocr_extraction.py — Module 1 (OCR Extraction)
 
Real OCR extraction logic. Same function signature as stub.py's run_ocr().
Combines mrz_parser.py (MRZ zone) + PaddleOCR/EasyOCR (visual zone) +
config/doc_types_config.json (which fields/strategy to use per doc_type).
 
Pipeline (Section 4 / Section 11 of the action plan):
    1. Decode + preprocess the image (deskew, crop, contrast — OpenCV).
    2. Look up the doc_type's strategy in doc_types_config.json.
    3. If the doc type has an MRZ (mrz_format != "none"):
         crop the MRZ band -> OCR it -> hand the lines to mrz_parser.parse_mrz()
       On success, MRZ fields win (they're checksum-backed and far more
       reliable than free-form visual OCR).
    4. Any expected_fields the MRZ didn't cover (or the whole set, for doc
       types with no MRZ, or when MRZ parsing failed) are filled by running
       a general OCR pass over the full image and matching label keywords.
    5. Build the Section 9b output contract and pick status:
       "success" (all expected fields present) / "partial" (some missing or
       low-confidence) / "failed" (nothing usable read at all).
 
This module never raises out of run_ocr() — a bad image or a missing OCR
engine yields status="failed", per Section 13's "every module must return a
defined failure state" rule.
"""
 
from __future__ import annotations
 
import json
import logging
import os
import re
from typing import Dict, List, Optional, Tuple
 
import numpy as np
 
import mrz_parser
 
logger = logging.getLogger(__name__)
 
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(_MODULE_DIR, "config", "doc_types_config.json")
 
# Fields we always try to pull from MRZ first when a doc type has one,
# because they live inside the MRZ layout itself (see mrz_parser.parse_td3 /
# parse_td1). Anything not in this set has to come from the visual zone.
_MRZ_SOURCED_FIELDS = {"name", "passport_number", "id_number", "nationality", "dob", "expiry", "gender"}
 
# Very small confidence floor/ceiling so downstream (risk engine) always
# gets a 0.0-1.0 float, per Section 9b's "confidence is always 0.0-1.0, no
# exceptions" rule.
_MRZ_FIELD_CONFIDENCE = 0.93   # checksum-verified MRZ read
_MRZ_FIELD_CONFIDENCE_UNVERIFIED = 0.75  # MRZ read, but checksum failed/n-a
_VISUAL_FIELD_CONFIDENCE_BASE = 0.55  # generic visual-zone OCR match
 
 
# --------------------------------------------------------------------------- #
# Config loading
# --------------------------------------------------------------------------- #
 
_config_cache: Optional[Dict] = None
 
 
def load_doc_type_config(doc_type: str, config_path: str = DEFAULT_CONFIG_PATH) -> Dict:
    """Load doc_types_config.json and return the entry for `doc_type`.
 
    Raises KeyError if `doc_type` isn't a recognized key — callers
    (run_ocr) turn that into a status="failed" result rather than letting
    it propagate.
    """
    global _config_cache
    if _config_cache is None:
        with open(config_path, "r", encoding="utf-8") as f:
            _config_cache = json.load(f)
    if doc_type not in _config_cache:
        raise KeyError(f"Unknown doc_type '{doc_type}'. Known types: {sorted(_config_cache)}")
    return _config_cache[doc_type]
 
 
# --------------------------------------------------------------------------- #
# Image preprocessing (OpenCV)
# --------------------------------------------------------------------------- #
 
def _decode_image(doc_image_bytes: bytes):
    import cv2  # local import: keep module importable even without cv2 installed
 
    arr = np.frombuffer(doc_image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode image bytes (unsupported/corrupt format).")
    return image
 
 
def _deskew(image):
    """Estimate and correct small rotation using the largest text-like blob's
    minimum-area bounding rectangle. Falls back to the original image if no
    reliable angle can be found (common on very clean/blank crops).
    """
    import cv2
 
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if coords.shape[0] < 50:
        return image
 
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
 
    # Small phone-photo tilts only — a huge "correction" usually means the
    # angle estimate is noise, not a real skew.
    if abs(angle) < 0.5 or abs(angle) > 15:
        return image
 
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
 
 
def _enhance_contrast(image):
    import cv2
 
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l_channel = clahe.apply(l_channel)
    merged = cv2.merge((l_channel, a_channel, b_channel))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
 
 
def preprocess_image(doc_image_bytes: bytes):
    """Decode -> deskew -> contrast-enhance. Returns an OpenCV BGR image.
 
    Deliberately conservative (Section 4's "must correctly parse MRZ even
    from imperfect phone-photo captures" edge case): we fix small rotation
    and low contrast, but we don't attempt aggressive binarization here,
    since that tends to help MRZ OCR and hurt visual-field OCR differently
    — each OCR call below does its own additional prep if it needs it.
    """
    image = _decode_image(doc_image_bytes)
    image = _deskew(image)
    image = _enhance_contrast(image)
    return image
 
 
def _crop_mrz_band(image):
    """Crop the bottom band of the document where the MRZ lives.
 
    MIDV-500-style full-page captures place the MRZ in roughly the bottom
    quarter of the frame for both TD3 (passport) and TD1 (ID card) layouts.
    This is a cheap, dependency-free heuristic crop; it errs on the side of
    including a bit more image than strictly necessary since OCR on a
    slightly oversized crop is harmless, whereas cropping too tight can
    slice off a line.
    """
    h, w = image.shape[:2]
    top = int(h * 0.72)
    return image[top:h, 0:w]
 
 
# --------------------------------------------------------------------------- #
# OCR engines (PaddleOCR primary, EasyOCR fallback)
# --------------------------------------------------------------------------- #
 
_paddle_engine = None
_easyocr_engine = None
 
 
def _get_paddle_engine():
    global _paddle_engine
    if _paddle_engine is None:
        from paddleocr import PaddleOCR  # heavy import, done lazily on first use
        _paddle_engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    return _paddle_engine
 
 
def _get_easyocr_engine():
    global _easyocr_engine
    if _easyocr_engine is None:
        import easyocr
        _easyocr_engine = easyocr.Reader(["en"], gpu=False)
    return _easyocr_engine
 
 
def _run_ocr_engine(image) -> List[Tuple[str, float]]:
    """Run whichever OCR engine is available over `image`.
 
    Returns a list of (text_line, confidence) tuples. Tries PaddleOCR first
    (per the action plan's tech stack), falls back to EasyOCR, and raises
    RuntimeError only if neither is installed — run_ocr() catches that and
    reports status="failed" rather than crashing the pipeline.
    """
    try:
        engine = _get_paddle_engine()
        result = engine.ocr(image, cls=True)
        lines: List[Tuple[str, float]] = []
        for page in result or []:
            for detection in page or []:
                text, confidence = detection[1][0], float(detection[1][1])
                lines.append((text, confidence))
        return lines
    except ImportError:
        logger.info("paddleocr not installed, falling back to easyocr")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("PaddleOCR failed (%s), falling back to easyocr", exc)
 
    try:
        engine = _get_easyocr_engine()
        result = engine.readtext(image)
        return [(text, float(confidence)) for (_box, text, confidence) in result]
    except ImportError as exc:
        raise RuntimeError(
            "Neither paddleocr nor easyocr is installed. "
            "Install one of them (pip install paddleocr  OR  pip install easyocr)."
        ) from exc
 
 
# --------------------------------------------------------------------------- #
# Visual-zone field extraction (non-MRZ fields, and MRZ fallback)
# --------------------------------------------------------------------------- #
 
# Loose label keywords per field, used to spot the right OCR line among the
# printed text. This is intentionally simple (regex/keyword heuristics, not
# a trained layout model) — appropriate for the hackathon's timeline, and
# it's the same "generic field-region OCR" fallback the action plan
# describes in Section 11 for doc types with no defined field layout.
_FIELD_LABEL_HINTS: Dict[str, List[str]] = {
    "name": ["name", "surname", "given name"],
    "nationality": ["nationality", "national"],
    "gender": ["sex", "gender"],
    "dob": ["date of birth", "dob", "birth"],
    "expiry": ["date of expiry", "expiry", "expiration", "valid until"],
    "passport_number": ["passport no", "passport number", "document no"],
    "id_number": ["id no", "identity no", "id number", "card no"],
    "license_number": ["license no", "licence no", "dl no"],
    "permit_number": ["permit no", "permit number"],
    "visa_number": ["visa no", "visa number"],
    "visa_type": ["visa type", "type of visa", "category"],
    "entry_validation": ["entries", "entry", "single entry", "multiple entry"],
    "stay_duration": ["duration of stay", "stay", "days"],
    "validity": ["valid", "validity"],
}
 
_DATE_PATTERN = re.compile(r"\b(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2})\b")
 
 
def _normalize_date_str(raw: str) -> Optional[str]:
    """Best-effort normalization of a printed date to ISO 8601 (Section 13)."""
    raw = raw.strip()
    iso_match = re.match(r"^\d{4}-\d{2}-\d{2}$", raw)
    if iso_match:
        return raw
    for sep in ("/", "-", "."):
        parts = raw.split(sep)
        if len(parts) == 3:
            a, b, c = parts
            if len(a) == 4:  # YYYY-MM-DD-ish
                y, m, d = a, b, c
            else:  # assume DD-MM-YYYY (common outside the US on travel docs)
                d, m, y = a, b, c
                if len(y) == 2:
                    y = ("20" + y) if int(y) < 50 else ("19" + y)
            try:
                from datetime import datetime
                return datetime(int(y), int(m), int(d)).strftime("%Y-%m-%d")
            except ValueError:
                return None
    return None
 
 
def extract_visual_fields(
    ocr_lines: List[Tuple[str, float]],
    fields_needed: List[str],
) -> Dict[str, Dict]:
    """Match printed OCR lines to the requested fields via label keywords.
 
    Returns {field_name: {"value": str, "confidence": float}} for every
    field it managed to find a plausible value for. Fields with no match are
    simply absent from the returned dict — run_ocr() fills those in as
    unread (confidence 0.0) when assembling the final output.
    """
    found: Dict[str, Dict] = {}
    lines_lower = [(text, conf, text.lower()) for text, conf in ocr_lines]
 
    for field in fields_needed:
        hints = _FIELD_LABEL_HINTS.get(field, [field])
        best: Optional[Tuple[str, float]] = None
 
        for idx, (text, conf, lower) in enumerate(lines_lower):
            if not any(hint in lower for hint in hints):
                continue
 
            value = None
            if field in ("dob", "expiry", "validity"):
                date_match = _DATE_PATTERN.search(text)
                if not date_match and idx + 1 < len(lines_lower):
                    date_match = _DATE_PATTERN.search(lines_lower[idx + 1][0])
                    if date_match:
                        conf = min(conf, lines_lower[idx + 1][1])
                if date_match:
                    value = _normalize_date_str(date_match.group(0))
            else:
                # Strip the matched label text itself, keep whatever's left;
                # if that's empty, the value is probably on the next line.
                stripped = text
                for hint in hints:
                    stripped = re.sub(re.escape(hint), "", stripped, flags=re.IGNORECASE)
                stripped = stripped.strip(" :.-")
                if stripped:
                    value = stripped
                elif idx + 1 < len(lines_lower):
                    value = lines_lower[idx + 1][0].strip()
                    conf = min(conf, lines_lower[idx + 1][1])
 
            if value:
                candidate = (value, conf)
                if best is None or candidate[1] > best[1]:
                    best = candidate
 
        if best is not None:
            found[field] = {"value": best[0], "confidence": round(best[1], 2)}
 
    return found
 
 
# --------------------------------------------------------------------------- #
# MRZ zone extraction (glue between preprocessing and mrz_parser)
# --------------------------------------------------------------------------- #
 
def extract_mrz_fields(image, mrz_format: str) -> Dict:
    """Crop the MRZ band, OCR it, and parse it via mrz_parser.parse_mrz().
 
    Returns mrz_parser.parse_mrz()'s result dict unchanged (success/fields/
    checksum_pass/mrz_raw); never raises.
    """
    if mrz_format == "none":
        return {"success": False, "fields": {}, "checksum_pass": None, "mrz_raw": None}
 
    try:
        mrz_crop = _crop_mrz_band(image)
        ocr_result = _run_ocr_engine(mrz_crop)
        raw_lines = [text for text, _conf in ocr_result]
        return mrz_parser.parse_mrz(raw_lines, mrz_format)
    except Exception as exc:
        logger.warning("MRZ extraction failed: %s", exc)
        return {"success": False, "fields": {}, "checksum_pass": None, "mrz_raw": None}
 
 
# --------------------------------------------------------------------------- #
# Public entry point — same signature as stub.py's run_ocr()
# --------------------------------------------------------------------------- #
 
def run_ocr(doc_image_bytes: bytes, doc_type: str) -> dict:
    """Module 1's real OCR extraction. Drop-in replacement for stub.run_ocr().
 
    Args:
        doc_image_bytes: raw bytes of the uploaded document image (jpeg/png).
        doc_type: one of the keys in config/doc_types_config.json
            ("passport", "visa", "national_id", "driving_license", "permit").
 
    Returns the Section 9b output contract:
        {
          "module": "ocr_extraction",
          "doc_type": doc_type,
          "status": "success" | "partial" | "failed",
          "extracted_fields": {field: {"value": ..., "confidence": 0.0-1.0}, ...},
          "mrz_raw": {"line1": ..., "line2": ..., ["line3": ...]}  # only if MRZ was read
        }
 
    Never raises — every failure path (unknown doc_type, undecodable image,
    missing OCR engine, no MRZ found, no visual text found) degrades to a
    "failed" or "partial" status instead of propagating an exception, per
    Section 13's module-contract rule.
    """
    try:
        config = load_doc_type_config(doc_type)
    except KeyError as exc:
        logger.error(str(exc))
        return {
            "module": "ocr_extraction",
            "doc_type": doc_type,
            "status": "failed",
            "extracted_fields": {},
            "mrz_raw": None,
        }
 
    expected_fields: List[str] = config["expected_fields"]
    mrz_format: str = config["mrz_format"]
 
    try:
        image = preprocess_image(doc_image_bytes)
    except Exception as exc:
        logger.error("Preprocessing failed for doc_type=%s: %s", doc_type, exc)
        return {
            "module": "ocr_extraction",
            "doc_type": doc_type,
            "status": "failed",
            "extracted_fields": {},
            "mrz_raw": None,
        }
 
    extracted: Dict[str, Dict] = {}
    mrz_raw = None
 
    # 1. MRZ zone first, when this doc type has one.
    if mrz_format != "none":
        mrz_result = extract_mrz_fields(image, mrz_format)
        if mrz_result["success"]:
            confidence = _MRZ_FIELD_CONFIDENCE if mrz_result["checksum_pass"] else _MRZ_FIELD_CONFIDENCE_UNVERIFIED
            for field, value in mrz_result["fields"].items():
                if field in expected_fields and value:
                    extracted[field] = {"value": value, "confidence": confidence}
            mrz_raw = mrz_result["mrz_raw"]
 
    # 2. Visual zone for anything the MRZ didn't cover (non-MRZ fields like
    #    visa_type/stay_duration, generic doc types with mrz_format="none",
    #    or MRZ fields that failed to read at all).
    missing_fields = [f for f in expected_fields if f not in extracted]
    if missing_fields:
        try:
            ocr_lines = _run_ocr_engine(image)
            visual_fields = extract_visual_fields(ocr_lines, missing_fields)
            for field, value in visual_fields.items():
                extracted[field] = value
        except RuntimeError as exc:
            # No OCR engine installed at all. If we also got nothing from
            # MRZ, this document is entirely unread -> failed. Otherwise we
            # still have partial MRZ results, so keep going and let the
            # status logic below mark it "partial".
            logger.error(str(exc))
            if not extracted:
                return {
                    "module": "ocr_extraction",
                    "doc_type": doc_type,
                    "status": "failed",
                    "extracted_fields": {},
                    "mrz_raw": None,
                }
 
    # 3. Status: success (everything expected was read), partial (some but
    #    not all), failed (nothing at all was read).
    if not extracted:
        status = "failed"
    elif all(f in extracted for f in expected_fields):
        status = "success"
    else:
        status = "partial"
 
    result = {
        "module": "ocr_extraction",
        "doc_type": doc_type,
        "status": status,
        "extracted_fields": extracted,
    }
    if mrz_raw is not None:
        result["mrz_raw"] = mrz_raw
    return result
 
 
if __name__ == "__main__":
    # Quick manual smoke test: python ocr_extraction.py <image_path> <doc_type>
    import sys
 
    if len(sys.argv) != 3:
        print("Usage: python ocr_extraction.py <image_path> <doc_type>")
        sys.exit(1)
 
    with open(sys.argv[1], "rb") as f:
        image_bytes = f.read()
 
    output = run_ocr(image_bytes, sys.argv[2])
    print(json.dumps(output, indent=2))
 
