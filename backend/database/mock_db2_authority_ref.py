"""
Mock DB #2 - authority-registered reference photo lookup.
Simulates an independent government biometric record (in reality: RFID/NFC
chip data). Used only by Module 5 (extension module). Explicitly a mock -
in a real deployment this is replaced by a chip read, not a database call
(see action_plan.pdf Section 7 - prototype vs real-world table).

Reference photos here are each person's own genuine selfie
(data/fixtures/faces/matched/<name>_selfie.jpg) - the "ground truth" of
what that person actually looks like, independent of whatever photo
appears on any document claiming to be theirs.
"""

AUTHORITY_REFERENCE_TABLE = {
    "F1000001": "data/fixtures/faces/matched/anoop_selfie.jpg",
    "F1000002": "data/fixtures/faces/matched/ashray_selfie.jpg",
    "F1000003": "data/fixtures/faces/matched/riya_selfie.jpg",
    "F1000004": "data/fixtures/faces/matched/srashti_selfie.jpg",
    "F1000005": "data/fixtures/faces/matched/yash_selfie.jpg",
}


def get_reference_photo_path(document_number: str):
    return AUTHORITY_REFERENCE_TABLE.get(document_number)