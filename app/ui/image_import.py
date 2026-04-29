from __future__ import annotations

from pathlib import Path


SUPPORTED_IMAGE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".webp",
}


def filter_supported_image_paths(paths: list[str]) -> list[str]:
    filtered_paths: list[str] = []
    for raw_path in paths:
        suffix = Path(raw_path).suffix.lower()
        if suffix in SUPPORTED_IMAGE_SUFFIXES:
            filtered_paths.append(raw_path)
    return filtered_paths

