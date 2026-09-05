"""
Convert MIDV-500 TIF source images into clean JPEG fixtures.

Run once per source image. Existing fixture JPGs are never overwritten,
which prevents accidental second-generation JPEG compression.

Source:
    data/midv500_subset/

Output:
    data/fixtures/clean/

Usage:
    python scripts/convert_midv500_to_fixtures.py
"""

from pathlib import Path

from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

SOURCE_DIR = PROJECT_ROOT / "data" / "midv500_subset"
OUTPUT_DIR = PROJECT_ROOT / "data" / "fixtures" / "clean"

JPEG_QUALITY = 92
SUPPORTED_EXTENSIONS = {".tif", ".tiff"}


def convert_all() -> None:
    """
    Convert every MIDV-500 TIF/TIFF into a single-generation JPEG fixture.

    The original directory structure under data/midv500 is preserved
    inside data/fixtures/clean.
    """

    if not SOURCE_DIR.exists():
        raise FileNotFoundError(
            f"Source directory not found: {SOURCE_DIR}"
        )

    tif_paths = sorted(
        (
            path
            for path in SOURCE_DIR.rglob("*")
            if path.is_file()
            and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ),
        key=lambda path: str(path).lower(),
    )

    if not tif_paths:
        print(f"No TIF/TIFF files found in {SOURCE_DIR}.")
        return

    converted = 0
    skipped = 0

    for tif_path in tif_paths:
        relative_path = tif_path.relative_to(SOURCE_DIR)
        output_path = OUTPUT_DIR / relative_path.with_suffix(".jpg")

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if output_path.exists():
            skipped += 1
            continue

        with Image.open(tif_path) as image:
            if getattr(image, "n_frames", 1) > 1:
                image.seek(0)

            image = image.convert("RGB")

            image.save(
                output_path,
                format="JPEG",
                quality=JPEG_QUALITY,
            )

        converted += 1

    print(f"Converted: {converted}")
    print(f"Skipped:   {skipped}")
    print(f"Output:    {OUTPUT_DIR}")

    print(
        "\nIMPORTANT: Do not reopen and resave the generated JPG fixtures. "
        "They must remain single-generation JPEGs for Module 3 ELA testing."
    )


if __name__ == "__main__":
    convert_all()