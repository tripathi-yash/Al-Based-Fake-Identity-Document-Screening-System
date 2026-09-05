"""
ocr_extraction.py — Module 1 (OCR Extraction), real implementation.

Function: convert a document image into structured field data
(Action Plan, Section 4 — Module 1).

CONSISTENCY FIX (earlier pass): run_ocr() takes raw IMAGE BYTES, not a
file path. routes.py calls run_ocr(doc_bytes, doc_type) — every other
module (3, 4, 5) also takes *_bytes: bytes as its first argument.

*** PADDLEOCR REMOVED — DO NOT RE-ADD IT ***
PaddleOCR 3.x requires a separate `paddlepaddle` inference-engine package
that is NOT installed by `pip install paddleocr` alone — without it,
PaddleOCR fails at construction with
    RuntimeError: Engine 'paddle_static' is unavailable because
    dependency 'paddlepaddle' is not installed.
On top of that, PaddleOCR 3.x's `.predict()` return shape has changed
across point releases and is not stable to code against with confidence.
EasyOCR works with zero extra native dependencies and is now the sole
primary engine below, with pytesseract as a lightweight fallback. If you
are tempted to re-add PaddleOCR: don't, unless you have a specific reason
and are willing to `pip install paddlepaddle` and re-verify its exact
`.predict()` result shape against your installed version first.

*** MRZ FRAGMENT-SPLITTING FIX (this pass) ***
Confirmed via direct debugging: EasyOCR's text detector frequently splits
ONE logical 44-char MRZ line into 2-3 separate bounding boxes (a gap in
the "<<<<" filler run is enough to break detection into multiple boxes).
The old code assumed each OCR-returned string WAS a complete line and
required it to fully match `^[A-Z0-9<]{20,44}$` — fragments never do,
so MRZ parsing silently failed 100% of the time and the code fell back
to the (also broken, see below) generic-field regex path. Fixed via
`_extract_mrz_band_lines()`, which clusters EasyOCR's raw detections by
row (Y-coordinate) and concatenates fragments left-to-right within each
row, reconstructing full lines regardless of how the fragments split.

*** GENERIC-FIELD EXTRACTION REWRITE (this pass) ***
The old `extract_generic_fields()` ran one regex against the ENTIRE
OCR'd text as a single joined blob. Two confirmed failure modes from
real output:
  1. Character classes containing `\s` match newlines too, so a capture
     group could greedily consume text across multiple OCR lines
     (observed: name captured as "SHARMA\nGIVEN NAME").
  2. re.search finds the FIRST matching label anywhere in the blob, even
     an unrelated occurrence (observed: passport_number captured
     "SURNAME" because the standalone word "PASSPORT" — the document
     title — matched before the real "Passport No." label, and the
     next line's text coincidentally fit the value pattern).
Fixed by matching LINE BY LINE: try same-line "Label: Value", then fall
back to "Label:" alone on one line with the value on the NEXT line —
matching how label/value pairs are actually rendered, and structurally
unable to bleed across unrelated fields.

Also fixed: date patterns only accepted DD/MM-first orderings; ISO
YYYY-MM-DD dates (as printed on our own fixtures) never matched. Colon
detection widened to also accept "=" (common OCR misread of ":").
Added a missing "passport_number" label pattern (previously absent
entirely, meaning the generic-OCR fallback could never recover it).

Pipeline:
    bytes -> decode -> shared preprocessing (backend/preprocessing/
             image_preprocess.py: preprocess_for_ocr — deskew,
             perspective-correct, contrast/glare normalize)
          -> config-driven dispatch on doc_type, using the SAME loader
             Module 2 uses (backend/modules/shared/
             doc_types_config_loader.py -> config/doc_types_config.json)
               -> mrz_format != "none": crop MRZ band, OCR it, parse with
                  mrz_parser.parse_mrz()
               -> generic field-region OCR for the visual zone / doc types
                  with no MRZ, or as a supplementary source
          -> assemble output in the exact Section 9b contract

Hard rules from the plan that this file must respect:
  * Never raise out of run_ocr() for a bad image — return status="failed"
    instead (Section 9b / Section 13).
  * Every extracted field carries a 0.0-1.0 confidence score, no
    exceptions (Section 9b) — feeds the risk engine's evidence-strength
    axis (Section 5).
  * Dates are always ISO 8601 (YYYY-MM-DD), never MRZ's raw YYMMDD.
  * doc-type field layout comes from config/doc_types_config.json via the
    shared loader, not hardcoded if/else branching (Section 11) — and not
    a locally-embedded duplicate copy.

Dependencies (OpenCV is required; OCR engines are optional and degrade
gracefully so this module stays importable/testable even before the
team has installed the heavier CV stack):
  - opencv-python-headless (required for decode + preprocessing)
  - easyocr                 (primary — visual-zone + MRZ-band text)
  - passporteye              (optional, purpose-built MRZ locator for TD3)
  - pytesseract              (lightweight fallback OCR engine)
"""

from __future__ import annotations

import os
import re
import tempfile
from typing import List, Optional, Tuple

from .mrz_parser import parse_mrz, ParsedMRZ

try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
except ImportError:  # pragma: no cover - environment-dependent
    _HAS_CV2 = False

try:
    from ...preprocessing.image_preprocess import preprocess_for_ocr
    _HAS_SHARED_PREPROCESSING = True
except ImportError:  # pragma: no cover - environment-dependent
    _HAS_SHARED_PREPROCESSING = False

    def preprocess_for_ocr(image):
        return image

try:
    from ..shared.doc_types_config_loader import load_doc_types_config
except ImportError:  # pragma: no cover - environment-dependent
    def load_doc_types_config():
        return {}

# Visual-zone OCR engine: EasyOCR primary, pytesseract fallback.
# See module docstring — PaddleOCR was tried and removed; do not re-add
# without re-reading that note.
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

try:
    from passporteye import read_mrz as _passporteye_read_mrz
    _HAS_PASSPORTEYE = True
except Exception:
    _HAS_PASSPORTEYE = False

_MRZ_LINE_PATTERN = re.compile(r"^[A-Z0-9<]{20,44}$")


# ---------------------------------------------------------------------------
# MRZ zone: locate + OCR + parse
# ---------------------------------------------------------------------------

def _ocr_text_lines(image) -> List[str]:
    """Run whichever OCR backend is available over an image crop and return
    a list of recognized text lines (best-effort, empty list on failure).
    Used for generic visual-zone OCR; the MRZ band uses
    _extract_mrz_band_lines() instead (see that function for why)."""
    if image is None or _OCR_BACKEND is None:
        return []
    try:
        if _OCR_BACKEND == "easyocr":
            result = _OCR_ENGINE.readtext(image, detail=0)
            return list(result)
        if _OCR_BACKEND == "pytesseract":
            text = _OCR_ENGINE.image_to_string(image)
            return [ln for ln in text.splitlines() if ln.strip()]
    except Exception:
        return []
    return []


def _extract_mrz_band_lines(band_image) -> List[str]:
    """
    Returns reconstructed MRZ lines from the cropped MRZ band, each
    intended to be a full 44-char TD3 line.

    EasyOCR's text detector frequently splits ONE logical MRZ line into
    multiple separate bounding boxes (confirmed via direct debugging —
    a gap in a "<<<<" filler run is enough to trigger a box split). A
    naive "one OCR string per line" assumption then produces fragments
    that never pass the full-line length check. Fixed here by using
    EasyOCR's bounding-box coordinates to cluster fragments into rows by
    vertical position, then concatenating fragments left-to-right within
    each row — reconstructing the original line regardless of how many
    boxes the detector split it into.

    Falls back to the simple one-string-per-line assumption for
    pytesseract, which doesn't expose per-fragment coordinates in the
    same way here.
    """
    if band_image is None or _OCR_BACKEND is None:
        return []

    if _OCR_BACKEND != "easyocr":
        return _ocr_text_lines(band_image)

    try:
        detections = _OCR_ENGINE.readtext(band_image, detail=1)  # [(bbox, text, conf), ...]
    except Exception:
        return []

    if not detections:
        return []

    # Cluster fragments into rows by vertical center. Tolerance chosen
    # empirically for a two-line MRZ band crop — widen if lines are
    # incorrectly merged, narrow if a single line splits into two rows.
    ROW_TOLERANCE_PX = 15
    rows = []  # each: {"y": running avg y-center, "fragments": [(x_left, text)]}
    for bbox, text, _conf in detections:
        xs = [pt[0] for pt in bbox]
        ys = [pt[1] for pt in bbox]
        x_left = min(xs)
        y_center = sum(ys) / len(ys)

        placed = False
        for row in rows:
            if abs(row["y"] - y_center) < ROW_TOLERANCE_PX:
                row["fragments"].append((x_left, text))
                row["y"] = (row["y"] + y_center) / 2
                placed = True
                break
        if not placed:
            rows.append({"y": y_center, "fragments": [(x_left, text)]})

    rows.sort(key=lambda r: r["y"])  # top-to-bottom
    lines = []
    for row in rows:
        row["fragments"].sort(key=lambda f: f[0])  # left-to-right within the row
        lines.append("".join(text for _, text in row["fragments"]))
    return lines


def _mrz_confidence_from_backend(image) -> float:
    """Best-effort average confidence for the MRZ read. Falls back to a
    conservative default when the backend doesn't expose per-token scores —
    every field needs a confidence, never omitted (Section 9b)."""
    if image is None or _OCR_BACKEND is None:
        return 0.5
    try:
        if _OCR_BACKEND == "easyocr":
            result = _OCR_ENGINE.readtext(image, detail=1)
            scores = [r[2] for r in result] if result else []
            return float(sum(scores) / len(scores)) if scores else 0.5
    except Exception:
        return 0.5
    return 0.6  # pytesseract has no simple per-line confidence in this call shape


def extract_mrz(image, mrz_format: str) -> Tuple[Optional[ParsedMRZ], float]:
    """Locate and OCR the MRZ band, then parse it structurally.
    Prefers PassportEye (purpose-built MRZ locator) for TD3 when available;
    otherwise crops the bottom band heuristically and OCRs it with the
    general-purpose engine. Returns (ParsedMRZ or None, confidence)."""
    if mrz_format in (None, "none"):
        return None, 0.0

    if _HAS_PASSPORTEYE and mrz_format in ("TD3", "TD3_or_none") and image is not None:
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                if _HAS_CV2:
                    cv2.imwrite(tmp.name, image)
                tmp_path = tmp.name
            mrz_obj = _passporteye_read_mrz(tmp_path)
            os.unlink(tmp_path)
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

    if not _HAS_CV2 or image is None:
        return None, 0.0
    try:
        h, w = image.shape[:2]
        band = image[int(h * 0.75):h, 0:w]  # MRZ sits in roughly the bottom 20-25%
        raw_lines = _extract_mrz_band_lines(band)
        candidate_lines = [re.sub(r"[^A-Z0-9<]", "", ln.upper()) for ln in raw_lines]
        candidate_lines = [ln for ln in candidate_lines if _MRZ_LINE_PATTERN.match(ln)]
        if not candidate_lines:
            return None, 0.0
        parsed = parse_mrz(candidate_lines, mrz_format)
        conf = _mrz_confidence_from_backend(band)
        return parsed, conf
    except Exception:
        return None, 0.0


# ---------------------------------------------------------------------------
# Generic visual-zone OCR
# ---------------------------------------------------------------------------
# Every pattern below MUST follow the template
#     r"(?:label_alt1|label_alt2|...)\s*[:=\-]?\s*(capture_group)"
# exactly — extract_generic_fields() below derives a "label-only" variant
# by splitting on this literal substring to detect a line that contains
# ONLY the label (value on the next OCR line). Breaking this template
# shape for a new entry will silently disable that fallback for it.

_LABEL_PATTERNS = {
    "name": r"(?:name|surname|full\s*name)\s*[:=\-]?\s*([A-Z][A-Z\s,.'-]{2,40})",
    "passport_number": r"(?:passport\s*(?:no\.?|number)?)\s*[:=\-]?\s*([A-Z0-9]{6,10})",
    "dob": r"(?:dob|date\s*of\s*birth|birth)\s*[:=\-]?\s*(\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}|\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
    "expiry": r"(?:expiry|exp(?:ires)?|valid\s*(?:until|thru))\s*[:=\-]?\s*(\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}|\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
    "license_number": r"(?:licen[cs]e\s*(?:no\.?|number)?)\s*[:=\-]?\s*([A-Z0-9\-]{5,20})",
    "id_number": r"(?:id\s*(?:no\.?|number)?)\s*[:=\-]?\s*([A-Z0-9\-]{5,20})",
    "permit_number": r"(?:permit\s*(?:no\.?|number)?)\s*[:=\-]?\s*([A-Z0-9\-]{5,20})",
    "visa_number": r"(?:visa\s*(?:no\.?|number)?)\s*[:=\-]?\s*([A-Z0-9\-]{5,20})",
    "visa_type": r"(?:visa\s*type|type)\s*[:=\-]?\s*([A-Z0-9\-]{1,15})",
    "entry_validation": r"(?:entry\s*validation)\s*[:=\-]?\s*([A-Z0-9\-/. ]{1,20})",
    "stay_duration": r"(?:stay|duration)\s*[:=\-]?\s*(\d{1,4}\s*(?:days|months|years))",
    "nationality": r"(?:nationality)\s*[:=\-]?\s*([A-Z]{2,20})",
    "gender": r"(?:sex|gender)\s*[:=\-]?\s*([MF])",
    "validity": r"(?:valid(?:ity)?)\s*[:=\-]?\s*(\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}|\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})",
}

_LABEL_TEMPLATE_SPLIT = r")\s*[:=\-]?\s*("


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


def extract_generic_fields(image, expected_fields: List[str]) -> dict:
    """Label-driven generic OCR extraction for fields not covered by MRZ
    (or the primary source for doc types with mrz_format == 'none').
    Returns {field: {"value", "confidence"}} only for fields it found.

    Matches LINE BY LINE (not against one joined blob) to avoid a capture
    group bleeding across unrelated OCR lines, and to avoid an unrelated
    earlier occurrence of a label word matching before the real one.
    Handles two layouts: "Label: Value" on one line, or "Label:" alone
    with the value on the following OCR line.
    """
    out: dict = {}
    if image is None:
        return out

    lines = _ocr_text_lines(image)
    if not lines:
        return out
    upper_lines = [ln.upper() for ln in lines]
    base_conf = _mrz_confidence_from_backend(image) if _OCR_BACKEND else 0.4

    for fname in expected_fields:
        pattern = _LABEL_PATTERNS.get(fname)
        if not pattern:
            continue

        label_only_pattern = None
        if _LABEL_TEMPLATE_SPLIT in pattern:
            label_part = pattern.split(_LABEL_TEMPLATE_SPLIT, 1)[0]
            label_only_pattern = label_part + r")\s*[:=\-]?\s*$"

        value = None
        for i, line in enumerate(upper_lines):
            same_line_match = re.search(pattern, line, re.IGNORECASE)
            if same_line_match and same_line_match.group(1).strip():
                value = same_line_match.group(1).strip()
                break

            if label_only_pattern and re.fullmatch(label_only_pattern, line.strip(), re.IGNORECASE):
                if i + 1 < len(upper_lines):
                    candidate = upper_lines[i + 1].strip()
                    if candidate:
                        value = candidate
                        break

        if value is None:
            continue

        if fname in ("dob", "expiry", "validity"):
            iso = _normalize_date(value)
            if iso is None:
                continue
            value = iso

        out[fname] = {"value": value, "confidence": round(min(max(base_conf, 0.3), 0.97), 2)}

    return out


# ---------------------------------------------------------------------------
# Top-level dispatcher — signature routes.py actually calls:
#     run_ocr(doc_bytes, doc_type)
# ---------------------------------------------------------------------------

def run_ocr(doc_image_bytes: bytes, doc_type: str, config: Optional[dict] = None) -> dict:
    """
    Convert document image BYTES into the Section 9b Module 1 output
    contract. Never raises. On any failure returns status="failed" with
    empty extracted_fields (Section 9b/13).
    """
    result = {
        "module": "ocr_extraction",
        "doc_type": doc_type,
        "status": "failed",
        "extracted_fields": {},
    }

    try:
        cfg = config or load_doc_types_config()
        doc_cfg = cfg.get(doc_type)
        if doc_cfg is None:
            return result  # unknown doc_type -> failed, don't guess

        expected_fields = doc_cfg.get("expected_fields", [])
        mrz_format = doc_cfg.get("mrz_format", "none")

        image = None
        if _HAS_CV2 and doc_image_bytes:
            arr = np.frombuffer(doc_image_bytes, dtype=np.uint8)
            image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        # if image is not None:
        #     image = preprocess_for_ocr(image)

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
                        extracted[fname] = {"value": mrz_field.value, "confidence": round(mrz_conf, 2)}

        # 2) Generic visual-zone OCR fills in whatever the MRZ pass missed.
        missing_fields = [f for f in expected_fields if f not in extracted]
        if missing_fields and image is not None:
            extracted.update(extract_generic_fields(image, missing_fields))

        result["extracted_fields"] = extracted
        if mrz_raw is not None:
            result["mrz_raw"] = mrz_raw

        found = len(extracted)
        total = len(expected_fields) if expected_fields else 1
        print(" Debug found extracted score : ", found)
        print(" Debug total expected_fields score : ", total)
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

if __name__ == "__main__":

    IMAGE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..",
    "data", "fixtures", "clean",
    "clean_passport_02.jpg"
)

    with open(IMAGE_PATH, "rb") as file:
        image_bytes = file.read()

    print(run_ocr(image_bytes, "passport"))