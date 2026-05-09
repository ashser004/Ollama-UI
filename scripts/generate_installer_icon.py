# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


ICON_SIZES = [
    (16, 16),
    (24, 24),
    (32, 32),
    (48, 48),
    (64, 64),
    (128, 128),
    (256, 256),
]


def convert_png_to_ico(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Source icon not found: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as image:
        image = image.convert("RGBA")
        image.save(destination, format="ICO", sizes=ICON_SIZES)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert the app PNG icon into a Windows ICO file."
    )
    parser.add_argument("source", type=Path, help="Path to the PNG source icon.")
    parser.add_argument(
        "destination", type=Path, help="Path where the ICO file should be written."
    )
    args = parser.parse_args()
    convert_png_to_ico(args.source, args.destination)


if __name__ == "__main__":
    main()