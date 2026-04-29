from pathlib import Path

from app.models import Note
from app.storage import FileNoteRepository


def test_repository_saves_and_reads_note(tmp_path: Path) -> None:
    repository = FileNoteRepository(base_dir=tmp_path)
    note = Note.create_empty()
    note.title = "Notatka testowa"
    note.content = "Linia 1\nLinia 2"
    note.image_paths = ["uploads/example/note.png"]

    repository.save(note)
    loaded = repository.get_note(note.id)

    assert loaded.id == note.id
    assert loaded.title == "Notatka testowa"
    assert loaded.content == "Linia 1\nLinia 2"
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
