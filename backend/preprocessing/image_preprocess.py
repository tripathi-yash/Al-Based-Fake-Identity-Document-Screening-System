"""
Shared OpenCV preprocessing: deskew, perspective-correct, crop to document
boundary, normalize contrast/glare. Used by BOTH Module 1 (OCR) and
Module 3 (tampering detection) - write once here, import in both, do not
duplicate this logic inside either module.
Owner: whoever builds Module 1, since OCR accuracy depends on it most directly.
"""

# TODO: implement using OpenCV
# import cv2
