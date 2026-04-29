from app.ui.image_import import filter_supported_image_paths


def test_filter_supported_image_paths_keeps_only_supported_images() -> None:
    paths = [
        "/tmp/note-1.jpg",
        "/tmp/note-2.PNG",
        "/tmp/document.pdf",
        "/tmp/archive.zip",
        "/tmp/photo.webp",
    ]

    filtered = filter_supported_image_paths(paths)

    assert filtered == [
        "/tmp/note-1.jpg",
        "/tmp/note-2.PNG",
        "/tmp/photo.webp",
    ]


def test_filter_supported_image_paths_returns_empty_list_for_unsupported_files() -> None:
    paths = [
        "/tmp/document.txt",
        "/tmp/presentation.pptx",
    ]

    assert filter_supported_image_paths(paths) == []
