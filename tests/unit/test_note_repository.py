from pathlib import Path

from app.models import Note
from app.storage import FileNoteRepository


def test_repository_saves_and_reads_note(tmp_path: Path) -> None:
    repository = FileNoteRepository(base_dir=tmp_path)
    note = Note.create_empty()
    note.title = "Notatka testowa"
    note.content = "Linia 1\nLinia 2"

    repository.save(note)
    loaded = repository.get_note(note.id)

    assert loaded.id == note.id
    assert loaded.title == "Notatka testowa"
    assert loaded.content == "Linia 1\nLinia 2"


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
