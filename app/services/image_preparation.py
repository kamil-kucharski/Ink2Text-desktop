from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from app.models import Note
from app.storage import FileNoteRepository


@dataclass(slots=True)
class PreparedImage:
    source_path: Path
    prepared_path: Path
    width: int
    height: int


@dataclass(slots=True)
class ImageQualityIssue:
    source_path: Path
    issue_code: str


class ImagePreparationService:
    def __init__(
        self,
        base_dir: Path | None = None,
        max_dimension: int = 1800,
        jpeg_quality: int = 90,
    ) -> None:
        self.base_dir = base_dir or Path.cwd() / "app_data"
        self.prepared_dir = self.base_dir / "prepared"
        self.prepared_dir.mkdir(parents=True, exist_ok=True)
        self.max_dimension = max_dimension
        self.jpeg_quality = jpeg_quality

    def prepare_note_images(
        self,
        note: Note,
        repository: FileNoteRepository,
    ) -> list[PreparedImage]:
        source_paths = [
            repository.resolve_image_path(relative_path)
            for relative_path in note.image_paths
        ]
        return self.prepare_images(note.id, source_paths)

    def analyze_note_image_quality(
        self,
        note: Note,
        repository: FileNoteRepository,
    ) -> list[ImageQualityIssue]:
        source_paths = [
            repository.resolve_image_path(relative_path)
            for relative_path in note.image_paths
        ]
        return self.analyze_image_quality(source_paths)

    def analyze_image_quality(self, source_paths: list[Path]) -> list[ImageQualityIssue]:
        image_module, _, image_ops_module = self._load_pillow_modules()
        try:
            from PIL import ImageStat
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Brakuje biblioteki Pillow. Zainstaluj zależności poleceniem: pip install -e .[dev]"
            ) from exc

        issues: list[ImageQualityIssue] = []
        for source_path in source_paths:
            if not source_path.is_file():
                continue

            with image_module.open(source_path) as image:
                image = image_ops_module.exif_transpose(image)
                width, height = image.size
                grayscale = image.convert("L")
                stat = ImageStat.Stat(grayscale)
                brightness = stat.mean[0]
                contrast = stat.stddev[0]

            if min(width, height) < 850:
                issues.append(ImageQualityIssue(source_path, "low_resolution"))
            if brightness < 55:
                issues.append(ImageQualityIssue(source_path, "too_dark"))
            elif brightness > 238:
                issues.append(ImageQualityIssue(source_path, "too_bright"))
            if contrast < 24:
                issues.append(ImageQualityIssue(source_path, "low_contrast"))

        return issues

    def prepare_images(self, note_id: str, source_paths: list[Path]) -> list[PreparedImage]:
        image_module, image_filter_module, image_ops_module = self._load_pillow_modules()

        note_output_dir = self.prepared_dir / note_id
        if note_output_dir.exists():
            shutil.rmtree(note_output_dir)
        note_output_dir.mkdir(parents=True, exist_ok=True)

        prepared_images: list[PreparedImage] = []
        for index, source_path in enumerate(source_paths, start=1):
            if not source_path.is_file():
                continue

            output_name = f"{index:02d}_{self._sanitize_stem(source_path.stem)}_prepared.jpg"
            output_path = note_output_dir / output_name

            with image_module.open(source_path) as image:
                image = image_ops_module.exif_transpose(image)
                image = image.convert("RGB")
                image = image_ops_module.autocontrast(image, cutoff=1)
                image = image.filter(image_filter_module.SHARPEN)

                if max(image.size) > self.max_dimension:
                    image.thumbnail((self.max_dimension, self.max_dimension))

                image.save(
                    output_path,
                    format="JPEG",
                    quality=self.jpeg_quality,
                    optimize=True,
                )
                width, height = image.size

            prepared_images.append(
                PreparedImage(
                    source_path=source_path,
                    prepared_path=output_path,
                    width=width,
                    height=height,
                )
            )

        return prepared_images

    def _load_pillow_modules(self):
        try:
            from PIL import Image, ImageFilter, ImageOps
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Brakuje biblioteki Pillow. Zainstaluj zależności poleceniem: pip install -e .[dev]"
            ) from exc

        return Image, ImageFilter, ImageOps

    def _sanitize_stem(self, stem: str) -> str:
        cleaned = "".join(char if char.isalnum() else "_" for char in stem.lower())
        normalized = "_".join(part for part in cleaned.split("_") if part)
        return normalized or "image"
