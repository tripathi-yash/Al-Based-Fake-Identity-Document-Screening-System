"""
ICAO 9303 MRZ checksum: weighted 7-3-1 formula, mod 10.
Isolated here so it can be unit tested independently.
Owner: fill in during Day 3.
"""

WEIGHTS = [7, 3, 1]


def char_to_value(c: str) -> int:
    """Map MRZ character to its numeric value per ICAO 9303: 0-9 -> itself,
    A-Z -> 10-35, '<' (filler) -> 0."""
    if c.isdigit():
        return int(c)
    if c.isalpha():
        return ord(c.upper()) - ord("A") + 10
    return 0  # '<' filler


def compute_check_digit(field: str) -> int:
    total = 0
    for i, c in enumerate(field):
        total += char_to_value(c) * WEIGHTS[i % 3]
    return total % 10


# TODO: apply to passport_number, dob, expiry, and composite field per ICAO 9303 Part 3
