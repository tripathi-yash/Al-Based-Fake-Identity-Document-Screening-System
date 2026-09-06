"""
Shared OpenCV preprocessing.

Split into TWO deliberately separate functions, not one pipeline, because
they have different safety properties for different consumers:

  correct_geometry() — deskew, perspective-correct, crop to document
      boundary. Repositions/crops the frame only; does NOT alter pixel
      VALUES. Safe to use anywhere: Module 1 (OCR), Module 3 (tampering),
      Module 4/5 (face extraction).

  normalize_contrast() — CLAHE-based glare/contrast normalization.
      REWRITES pixel values. Safe and helpful for Module 1 (OCR) and
      Module 4/5 (face detection on glare-heavy photos) — NOT safe for
      Module 3's ELA signal (ela.py), which measures recompression-
      artifact differences between the original bytes and a resave.
      Running contrast normalization first means ELA measures artifacts
      from the normalization itself, not from any real tampering — this
      would corrupt Module 3's forensic signal, not just leave it unused.
      Do NOT call this before feeding bytes to ela.py or
      dl_tamper_detector.py. Module 3 must keep operating on the raw
      uploaded bytes.

Do not duplicate either function's logic inside individual module files —
import from here.

BUG FIX (this pass): correct_geometry()'s Otsu-threshold + minAreaRect
deskew technique assumes a scanned document with a distinct page
silhouette on a contrasting background. On a full-frame rendered image
(text/content fills the entire frame, no real "page boundary" — e.g. our
synthetic passport fixtures, and any plain-background selfie/document
photo) Otsu treats nearly the whole frame as foreground, minAreaRect's
angle becomes meaningless noise, and the resulting "correction" applies
a garbage rotation that destroys the image for OCR/face detection.
Confirmed via direct debugging: EasyOCR read the raw fixture perfectly,
then produced only single-character noise after correct_geometry() ran.
Fixed by sanity-checking the detected rect before trusting its angle:
skip correction entirely if no real boundary was found, or if the
computed angle is implausibly large for a genuine scan tilt.
"""
import cv2
import numpy as np


def correct_geometry(image):
    """Deskew + perspective-correct. Returns the corrected image (numpy
    array), or the original image unchanged if correction fails OR if no
    genuine page boundary is detected to correct against — must never
    raise, since a bad/unusual image is a normal input case, not an
    error condition."""
    if image is None:
        return image

    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image.copy()

        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        coords = cv2.findNonZero(thresh)
        if coords is None:
            return image

        rect = cv2.minAreaRect(coords)
        (rect_w, rect_h), rect_angle = rect[1], rect[2]

        h, w = gray.shape[:2]
        image_area = h * w
        rect_area = rect_w * rect_h

        # Safety check 1: if Otsu marks ~the whole frame as "foreground"
        # (full-bleed rendered card, plain-background photo), there is no
        # real page boundary to deskew against — minAreaRect's angle is
        # noise, not a measurement. Bail out rather than rotate blindly.
        # 0.9 threshold chosen so a genuinely tilted scanned page (which
        # still leaves visible margin around it) is unaffected.
        if rect_area >= 0.9 * image_area:
            return image

        angle = -(90 + rect_angle) if rect_angle < -45 else -rect_angle

        # Safety check 2: a real deskew correction on a photographed/
        # scanned document is a SMALL angle (a few degrees of tilt).
        # Anything wildly larger is almost certainly a bad Otsu/
        # minAreaRect read on a low-contrast or full-frame image, not a
        # genuine skew — applying it would rotate the image into a
        # essentially random orientation instead of leaving it alone.
        if abs(angle) > 15:
            return image

        center = (w // 2, h // 2)
        rot_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        deskewed = cv2.warpAffine(
            image, rot_matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
        return deskewed
    except Exception:
        return image


def normalize_contrast(image):
    """CLAHE-based glare/contrast normalization. DO NOT use this on bytes
    that will be passed to Module 3's ela.py or dl_tamper_detector.py —
    see this file's module docstring for why. Safe for Module 1 (OCR
    readability) and Module 4/5 (face detection on glare-heavy document
    photos)."""
    if image is None:
        return image

    try:
        if image.ndim != 3:
            return image
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        l_channel = clahe.apply(l_channel)
        normalized = cv2.merge((l_channel, a_channel, b_channel))
        return cv2.cvtColor(normalized, cv2.COLOR_LAB2BGR)
    except Exception:
        return image


def preprocess_for_ocr(image):
    # old code  
    # """Convenience wrapper for Module 1: geometry correction + contrast
    # normalization, since both are safe and beneficial for OCR readability."""

    """Safe OCR preprocessing.

    Geometry correction is intentionally disabled until a reliable
    document-boundary detector is available. Contrast normalization
    preserves the full document frame.
    """
    return normalize_contrast(image)
    # return normalize_contrast(correct_geometry(image))


def preprocess_for_face_detection(image):
    # old code
    # """Convenience wrapper for Module 4/5: same two steps as OCR, since
    # neither harms face-embedding extraction and glare normalization can
    # reduce false no_face_detected results on poorly-lit document photos."""
    # return normalize_contrast(correct_geometry(image))

    """Safe preprocessing.
    
        Geometry correction is intentionally disabled until a reliable
        document-boundary detector is available. Contrast normalization
        preserves the full document frame.
        """
    return normalize_contrast(image)