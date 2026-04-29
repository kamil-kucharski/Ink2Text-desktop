from pathlib import Path

from app.services import ImagePreparationService


class FakeImage:
    def __init__(self, size: tuple[int, int]) -> None:
        self.size = size

    def __enter__(self) -> "FakeImage":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def convert(self, _mode: str) -> "FakeImage":
        return self

    def filter(self, _value) -> "FakeImage":
        return self

    def thumbnail(self, bounds: tuple[int, int]) -> None:
        max_width, max_height = bounds
        scale = min(max_width / self.size[0], max_height / self.size[1])
        self.size = (
            max(1, int(self.size[0] * scale)),
            max(1, int(self.size[1] * scale)),
        )

    def save(self, output_path: Path, **_kwargs) -> None:
        output_path.write_bytes(b"prepared-image")


class FakeImageModule:
    @staticmethod
    def open(_path: Path) -> FakeImage:
        return FakeImage((2400, 1200))


class FakeImageFilterModule:
    SHARPEN = object()


class FakeImageOpsModule:
    @staticmethod
    def exif_transpose(image: FakeImage) -> FakeImage:
        return image

    @staticmethod
    def autocontrast(image: FakeImage, cutoff: int = 0) -> FakeImage:
        return image


def test_prepare_images_creates_ordered_outputs(tmp_path: Path) -> None:
    service = ImagePreparationService(base_dir=tmp_path, max_dimension=1000)
    service._load_pillow_modules = lambda: (
        FakeImageModule,
        FakeImageFilterModule,
        FakeImageOpsModule,
    )

    first = tmp_path / "Bardzo wazna notatka.png"
    second = tmp_path / "chemia-final.jpg"
    first.write_bytes(b"source-1")
    second.write_bytes(b"source-2")

    prepared = service.prepare_images("note-123", [first, second])

    assert len(prepared) == 2
    assert prepared[0].prepared_path.name == "01_bardzo_wazna_notatka_prepared.jpg"
    assert prepared[1].prepared_path.name == "02_chemia_final_prepared.jpg"
    assert prepared[0].prepared_path.exists()
    assert prepared[0].width == 1000
    assert prepared[0].height == 500


def test_prepare_images_replaces_previous_cache_for_note(tmp_path: Path) -> None:
    service = ImagePreparationService(base_dir=tmp_path, max_dimension=1000)
    service._load_pillow_modules = lambda: (
        FakeImageModule,
        FakeImageFilterModule,
        FakeImageOpsModule,
    )

    existing_dir = tmp_path / "prepared" / "note-123"
    existing_dir.mkdir(parents=True)
    stale_file = existing_dir / "stale.jpg"
    stale_file.write_bytes(b"old")

    source = tmp_path / "nowa.png"
    source.write_bytes(b"source")

    prepared = service.prepare_images("note-123", [source])

    assert len(prepared) == 1
    assert not stale_file.exists()
