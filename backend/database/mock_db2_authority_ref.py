"""
Mock DB #2 - authority-registered reference photo lookup.
Simulates an independent government biometric record (in reality: RFID/NFC
chip data). Used only by Module 5 (extension module). Explicitly a mock -
in a real deployment this is replaced by a chip read, not a database call
(see action_plan.pdf Section 7 - prototype vs real-world table).
Owner: fill in only if/when Module 5 is built (after Modules 1-4 stable).
"""

# TODO: map document_number -> path of the ORIGINAL unedited MIDV-500 photo
# (i.e. before your team's photo-swap edits), per action_plan.pdf Section 12
AUTHORITY_REFERENCE_TABLE = {
    # "P1234567": "data/fixtures/clean/original_midv500_photo_01.jpg",
    "N1234567": "data/raw_selfies/ashray.jpg",
    "F1000001": "data/fixtures/faces/matched/anoop_selfie.jpg",
    "F1000002": "data/fixtures/faces/matched/ashray_selfie.jpg",
    "F1000003": "data/fixtures/faces/matched/riya_selfie.jpg",
    "F1000004": "data/fixtures/faces/matched/srashti_selfie.jpg",
    "F1000005": "data/fixtures/faces/matched/yash_selfie.jpg",
}

def get_reference_photo_path(document_number: str):
    return AUTHORITY_REFERENCE_TABLE.get(document_number)
