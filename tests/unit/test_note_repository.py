from pathlib import Path

from app.models import Note
from app.storage import FileNoteRepository


def test_repository_saves_and_reads_note(tmp_path: Path) -> None:
    repository = FileNoteRepository(base_dir=tmp_path)
    note = Note.create_empty()
    note.title = "Notatka testowa"
    note.content = "<p><strong>Linia 1</strong></p><p>Linia 2</p>"
    note.content_format = "html"
    note.image_paths = ["uploads/example/note.png"]

    repository.save(note)
    loaded = repository.get_note(note.id)

    assert loaded.id == note.id
    assert loaded.title == "Notatka testowa"
    assert loaded.content == "<p><strong>Linia 1</strong></p><p>Linia 2</p>"
    assert loaded.content_format == "html"
    assert loaded.image_paths == ["uploads/example/note.png"]


def test_repository_lists_latest_notes_first(tmp_path: Path) -> None:
    repository = FileNoteRepository(base_dir=tmp_path)
    older = Note.create_empty()
    older.title = "Starsza"
    newer = Note.create_empty()
    newer.title = "Nowsza"

    repository.save(older)
    repository.save(newer)

    notes = repository.list_notes()

    assert len(notes) == 2
    assert notes[0].id == newer.id


def test_repository_imports_images_into_app_storage(tmp_path: Path) -> None:
    repository = FileNoteRepository(base_dir=tmp_path)
    note = Note.create_empty()
    source_image = tmp_path / "source.png"
    source_image.write_bytes(b"fake-image")

    imported = repository.import_images(note, [str(source_image)])

    assert len(imported) == 1
    assert imported[0].startswith(f"uploads/{note.id}/")
    assert note.image_paths == imported
    assert repository.resolve_image_path(imported[0]).read_bytes() == b"fake-image"


def test_repository_removes_image_from_note_and_disk(tmp_path: Path) -> None:
    repository = FileNoteRepository(base_dir=tmp_path)
    note = Note.create_empty()
    source_image = tmp_path / "source.png"
    source_image.write_bytes(b"fake-image")
    imported = repository.import_images(note, [str(source_image)])

    repository.remove_image(note, imported[0])

    assert note.image_paths == []
    assert not repository.resolve_image_path(imported[0]).exists()


def test_repository_moves_image_within_note_order(tmp_path: Path) -> None:
    repository = FileNoteRepository(base_dir=tmp_path)
    note = Note.create_empty()
    note.image_paths = [
        "uploads/a.png",
        "uploads/b.png",
        "uploads/c.png",
    ]

    moved = repository.move_image(note, "uploads/b.png", -1)

    assert moved is True
    assert note.image_paths == [
        "uploads/b.png",
        "uploads/a.png",
        "uploads/c.png",
    ]


def test_repository_does_not_move_image_outside_bounds(tmp_path: Path) -> None:
    repository = FileNoteRepository(base_dir=tmp_path)
    note = Note.create_empty()
    note.image_paths = [
        "uploads/a.png",
        "uploads/b.png",
    ]

    moved = repository.move_image(note, "uploads/a.png", -1)

    assert moved is False
    assert note.image_paths == [
        "uploads/a.png",
        "uploads/b.png",
    ]


def test_repository_deletes_note_and_related_directories(tmp_path: Path) -> None:
    repository = FileNoteRepository(base_dir=tmp_path)
    note = Note.create_empty()
    note.title = "Do usunięcia"
    repository.save(note)

    note_upload_dir = repository.uploads_dir / note.id
    note_upload_dir.mkdir(parents=True, exist_ok=True)
    (note_upload_dir / "photo.jpg").write_bytes(b"image")

    prepared_dir = repository.base_dir / "prepared" / note.id
    prepared_dir.mkdir(parents=True, exist_ok=True)
    (prepared_dir / "prepared.jpg").write_bytes(b"prepared")

    repository.delete(note.id)

    assert not repository.has_note(note.id)
    assert not note_upload_dir.exists()
    assert not prepared_dir.exists()


def test_repository_moves_note_to_trash_and_restores_it(tmp_path: Path) -> None:
    repository = FileNoteRepository(base_dir=tmp_path)
    note = Note.create_empty()
    note.title = "Do kosza"
    repository.save(note)

    repository.move_to_trash(note.id)

    assert not repository.has_note(note.id)
    assert repository.has_trashed_note(note.id)
    assert [trashed.id for trashed in repository.list_trashed_notes()] == [note.id]

    repository.restore_from_trash(note.id)

    assert repository.has_note(note.id)
    assert not repository.has_trashed_note(note.id)


def test_repository_deletes_trashed_note_permanently(tmp_path: Path) -> None:
    repository = FileNoteRepository(base_dir=tmp_path)
    note = Note.create_empty()
    note.title = "Do trwałego usunięcia"
    repository.save(note)

    note_upload_dir = repository.uploads_dir / note.id
    note_upload_dir.mkdir(parents=True, exist_ok=True)
    (note_upload_dir / "photo.jpg").write_bytes(b"image")

    repository.move_to_trash(note.id)
    repository.delete_from_trash(note.id)

    assert not repository.has_note(note.id)
    assert not repository.has_trashed_note(note.id)
    assert not note_upload_dir.exists()
