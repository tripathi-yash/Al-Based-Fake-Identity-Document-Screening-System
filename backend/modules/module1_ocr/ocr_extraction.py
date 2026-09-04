"""
ocr_extraction.py — Module 1 (OCR Extraction), real implementation.

Function: convert a document image into structured field data
(Action Plan, Section 4 — Module 1).

Pipeline:
    image -> OpenCV preprocessing (deskew, perspective-correct, contrast)
          -> config-driven dispatch on doc_type (Section 11)
               -> mrz_format != "none": crop MRZ band, OCR it, parse with
                  mrz_parser.parse_mrz()
               -> generic field-region OCR for the visual zone / doc types
                  with no MRZ (driving_license, permit) or as a
                  text/MRZ cross-check source for doc types that have one
          -> assemble output in the exact Section 9b contract

Hard rules from the plan that this file must respect:
  * Never raise out of extract_ocr() for a bad image — return
    status="failed" instead (Section 9b / Section 13).
  * Every extracted field carries a 0.0-1.0 confidence score, no exceptions
    (Section 9b) — this feeds the risk engine's evidence-strength axis
    (Section 5).
  * Dates are always ISO 8601 (YYYY-MM-DD), never MRZ's raw YYMMDD or any
    other format (Section 13's #1 listed failure case).
  * doc-type field layout comes from doc_types_config.json, not hardcoded
    if/else branching (Section 11) — Modules 3/4/5/6 stay doc-type agnostic;
    only Module 1 (and 2) branch on doc_type, and they do it via config.

Optional dependencies (OpenCV is required; the OCR engines are optional and
degrade gracefully so this module is importable/testable even before the
team has installed the heavier CV stack — matching the Day 2 stub-first
philosophy of Section 9a: the function signature and output shape are what
matter first, real accuracy comes in after Day 3):
  - opencv-python       (required for preprocessing)
  - paddleocr / easyocr (either one, for visual-zone text)
  - passporteye          (optional, for a purpose-built MRZ locator on TD3)
  - pytesseract           (fallback OCR engine)
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

from .mrz_parser import parse_mrz, ParsedMRZ

try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
except ImportError:  # pragma: no cover - environment-dependent
    _HAS_CV2 = False

# Visual-zone OCR engine: try PaddleOCR first, then EasyOCR, then pytesseract.
_OCR_ENGINE = None
_OCR_BACKEND = None
try:
    from paddleocr import PaddleOCR
    _OCR_ENGINE = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    _OCR_BACKEND = "paddleocr"
except Exception:
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

try:
    from passporteye import read_mrz as _passporteye_read_mrz
    _HAS_PASSPORTEYE = True
except Exception:
    _HAS_PASSPORTEYE = False


_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "doc_types_config.json")
_MRZ_LINE_PATTERN = re.compile(r"^[A-Z0-9<]{20,44}$")


def load_config(path: str = _CONFIG_PATH) -> dict:
    """Load doc_types_config.json (Section 11) — the single source of truth
    for per-doc-type field layout, MRZ format, and validation rules."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Preprocessing (Section 3: "Preprocessing: OpenCV deskew, perspective-
# correct, glare normalize" — shared by every module that consumes the image)
# ---------------------------------------------------------------------------

def preprocess_image(image):
    """Deskew, perspective-correct, and normalize contrast/glare.

    Returns the processed image (numpy array), or the original image
    unchanged if OpenCV isn't available or preprocessing fails — this must
    never raise, since a bad/unusual image is exactly the case Module 1
    has to handle gracefully (Section 4's edge cases: "imperfect phone-photo
    captures").
    """
    if not _HAS_CV2 or image is None:
        return image

    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()

        # Deskew via minAreaRect over thresholded text-like pixels.
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        coords = cv2.findNonZero(thresh)
        angle = 0.0
        if coords is not None:
            rect_angle = cv2.minAreaRect(coords)[-1]
            angle = -(90 + rect_angle) if rect_angle < -45 else -rect_angle
        (h, w) = gray.shape[:2]
        center = (w // 2, h // 2)
        rot_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        deskewed = cv2.warpAffine(
            image, rot_matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )

        # Glare / contrast normalization: CLAHE on the luminance channel.
        lab = cv2.cvtColor(deskewed, cv2.COLOR_BGR2LAB) if deskewed.ndim == 3 else None
        if lab is not None:
            l_channel, a_channel, b_channel = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            l_channel = clahe.apply(l_channel)
            normalized = cv2.merge((l_channel, a_channel, b_channel))
            normalized = cv2.cvtColor(normalized, cv2.COLOR_LAB2BGR)
        else:
            normalized = deskewed

        return normalized
    except Exception:
        # Preprocessing must degrade, never break the pipeline (Section 13).
        return image


# ---------------------------------------------------------------------------
# MRZ zone: locate + OCR + parse
# ---------------------------------------------------------------------------

def _ocr_text_lines(image) -> list[str]:
    """Run whichever OCR backend is available over an image crop and return
    a list of recognized text lines (best-effort, empty list on failure)."""
    if image is None or _OCR_BACKEND is None:
        return []
    try:
        if _OCR_BACKEND == "paddleocr":
            result = _OCR_ENGINE.ocr(image, cls=True)
            lines = [line[1][0] for block in result for line in block] if result else []
            return lines
        if _OCR_BACKEND == "easyocr":
            result = _OCR_ENGINE.readtext(image, detail=0)
            return list(result)
        if _OCR_BACKEND == "pytesseract":
            text = _OCR_ENGINE.image_to_string(image)
            return [ln for ln in text.splitlines() if ln.strip()]
    except Exception:
        return []
    return []


def _mrz_confidence_from_backend(image) -> float:
    """Best-effort average confidence for the MRZ read. Falls back to a
    conservative default when the backend doesn't expose per-token scores —
    Section 9b requires a confidence on every field, never omitted."""
    if image is None or _OCR_BACKEND is None:
        return 0.5
    try:
        if _OCR_BACKEND == "paddleocr":
            result = _OCR_ENGINE.ocr(image, cls=True)
            scores = [line[1][1] for block in result for line in block] if result else []
            return float(sum(scores) / len(scores)) if scores else 0.5
        if _OCR_BACKEND == "easyocr":
            result = _OCR_ENGINE.readtext(image, detail=1)
            scores = [r[2] for r in result] if result else []
            return float(sum(scores) / len(scores)) if scores else 0.5
    except Exception:
        return 0.5
    return 0.6  # pytesseract has no simple per-line confidence in this call shape


def extract_mrz(image, mrz_format: str) -> tuple[Optional[ParsedMRZ], float]:
    """Locate and OCR the MRZ band, then parse it structurally.

    Prefers PassportEye (purpose-built MRZ locator) for TD3 when available;
    otherwise crops the bottom band of the image heuristically and OCRs it
    with the general-purpose engine, splitting into MRZ-shaped lines.
    Returns (ParsedMRZ or None, confidence).
    """
    if mrz_format in (None, "none"):
        return None, 0.0

    # Preferred path: PassportEye, purpose-built for TD3 MRZ localization.
    if _HAS_PASSPORTEYE and mrz_format in ("TD3", "TD3_or_none") and image is not None:
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                if _HAS_CV2:
                    cv2.imwrite(tmp.name, image)
                mrz_obj = _passporteye_read_mrz(tmp.name)
            os.unlink(tmp.name)
            if mrz_obj is not None:
                raw_text = mrz_obj.aux.get("text", "") if hasattr(mrz_obj, "aux") else ""
                lines = [ln for ln in raw_text.splitlines() if ln.strip()]
                if len(lines) >= 2:
                    parsed = parse_mrz(lines[:2], "TD3")
                    conf = float(getattr(mrz_obj, "valid_score", 70)) / 100.0
                    if parsed is not None:
                        return parsed, conf
        except Exception:
            pass  # fall through to the generic crop-and-OCR path

    # Fallback: heuristic bottom-band crop + generic OCR, then structural parse.
    if not _HAS_CV2 or image is None:
        return None, 0.0
    try:
        h, w = image.shape[:2]
        # MRZ sits in roughly the bottom 20-25% of a well-cropped ID document.
        band = image[int(h * 0.75):h, 0:w]
        raw_lines = _ocr_text_lines(band)
        candidate_lines = [
            re.sub(r"[^A-Z0-9<]", "", ln.upper()) for ln in raw_lines
        ]
        candidate_lines = [ln for ln in candidate_lines if _MRZ_LINE_PATTERN.match(ln)]
        if not candidate_lines:
            return None, 0.0
        parsed = parse_mrz(candidate_lines, mrz_format)
        conf = _mrz_confidence_from_backend(band)
        return parsed, conf
    except Exception:
        return None, 0.0


# ---------------------------------------------------------------------------
# Generic visual-zone OCR (for driving_license/permit, and as a supplementary
# text source used by the text/MRZ cross-check that Module 2 performs)
# ---------------------------------------------------------------------------

_LABEL_PATTERNS = {
    "name": r"(?:name|surname|full\s*name)\s*[:\-]?\s*([A-Z][A-Z\s,.'-]{2,40})",
    "dob": r"(?:dob|date\s*of\s*birth|birth)\s*[:\-]?\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
    "expiry": r"(?:expiry|exp(?:ires)?|valid\s*(?:until|thru))\s*[:\-]?\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
    "license_number": r"(?:licen[cs]e\s*(?:no\.?|number)?)\s*[:\-]?\s*([A-Z0-9\-]{5,20})",
    "id_number": r"(?:id\s*(?:no\.?|number)?)\s*[:\-]?\s*([A-Z0-9\-]{5,20})",
    "permit_number": r"(?:permit\s*(?:no\.?|number)?)\s*[:\-]?\s*([A-Z0-9\-]{5,20})",
    "visa_number": r"(?:visa\s*(?:no\.?|number)?)\s*[:\-]?\s*([A-Z0-9\-]{5,20})",
    "visa_type": r"(?:visa\s*type|type)\s*[:\-]?\s*([A-Z0-9\-]{1,15})",
    "stay_duration": r"(?:stay|duration)\s*[:\-]?\s*(\d{1,4}\s*(?:days|months|years))",
    "nationality": r"(?:nationality)\s*[:\-]?\s*([A-Z]{2,20})",
    "gender": r"(?:sex|gender)\s*[:\-]?\s*([MF])",
    "validity": r"(?:valid(?:ity)?)\s*[:\-]?\s*(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
}


def _normalize_date(raw: str) -> Optional[str]:
    """Best-effort conversion of a free-text date into ISO 8601. Returns
    None (never a malformed string) if the format can't be confidently
    resolved — a missing field is safer than a wrong one downstream."""
    raw = raw.strip()
    for sep in ("/", "-", "."):
        if sep in raw:
            parts = raw.split(sep)
            if len(parts) == 3:
                a, b, c = parts
                # Prefer the unambiguous YYYY-first case.
                if len(a) == 4:
                    y, m, d = a, b, c
                else:
                    d, m, y = a, b, c
                    if len(y) == 2:
                        y = ("19" if int(y) > 30 else "20") + y
                try:
                    y, m, d = int(y), int(m), int(d)
                    return f"{y:04d}-{m:02d}-{d:02d}"
                except ValueError:
                    return None
    return None


def extract_generic_fields(image, expected_fields: list[str]) -> dict:
    """Label-driven generic OCR extraction for doc types without a
    fully-specified layout (Section 11: national_id/driving_license/permit
    are 'secondary, generic-OCR-only'). Returns {field: {"value", "confidence"}}
    only for fields it found — the caller fills in the rest as unreadable.
    """
    out: dict = {}
    if image is None:
        return out

    lines = _ocr_text_lines(image)
    full_text = "\n".join(lines).upper()
    base_conf = _mrz_confidence_from_backend(image) if _OCR_BACKEND else 0.4

    for fname in expected_fields:
        pattern = _LABEL_PATTERNS.get(fname)
        if not pattern:
            continue
        match = re.search(pattern, full_text, re.IGNORECASE)
        if not match:
            continue
        value = match.group(1).strip()
        if fname in ("dob", "expiry", "validity"):
            iso = _normalize_date(value)
            if iso is None:
                continue
            value = iso
        out[fname] = {"value": value, "confidence": round(min(max(base_conf, 0.3), 0.97), 2)}

    return out


# ---------------------------------------------------------------------------
# Top-level dispatcher — the single entry point every stub/real swap in
# Section 9a's mock-first strategy must keep this exact signature.
# ---------------------------------------------------------------------------

def extract_ocr(image_path: str, doc_type: str, config: Optional[dict] = None) -> dict:
    """Convert a document image into the Section 9b Module 1 output contract.

    Never raises. On any failure returns status="failed" with empty
    extracted_fields, per Section 9b/13 ("never throw an exception for a
    bad image, return 'failed' instead").
    """
    result = {
        "module": "ocr_extraction",
        "doc_type": doc_type,
        "status": "failed",
        "extracted_fields": {},
    }

    try:
        cfg = config or load_config()
        doc_cfg = cfg.get(doc_type)
        if doc_cfg is None:
            return result  # unknown doc_type -> failed, don't guess

        expected_fields = doc_cfg.get("expected_fields", [])
        mrz_format = doc_cfg.get("mrz_format", "none")

        image = None
        if _HAS_CV2 and os.path.exists(image_path):
            image = cv2.imread(image_path)
        if image is not None:
            image = preprocess_image(image)

        extracted: dict = {}
        mrz_raw = None

        # 1) MRZ zone, when this doc type has one.
        if mrz_format != "none":
            parsed_mrz, mrz_conf = extract_mrz(image, mrz_format)
            if parsed_mrz is not None:
                mrz_raw = parsed_mrz.as_raw_dict()
                for fname in expected_fields:
                    mrz_field = parsed_mrz.fields.get(fname)
                    if mrz_field is not None and mrz_field.value:
                        extracted[fname] = {
                            "value": mrz_field.value,
                            "confidence": round(mrz_conf, 2),
                        }

        # 2) Generic visual-zone OCR fills in whatever the MRZ pass missed
        #    (or is the primary source when mrz_format == "none").
        missing_fields = [f for f in expected_fields if f not in extracted]
        if missing_fields and image is not None:
            generic = extract_generic_fields(image, missing_fields)
            extracted.update(generic)

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
        # Absolute last resort — the one rule this module cannot break.
        result["status"] = "failed"
        result["extracted_fields"] = {}
        return result
