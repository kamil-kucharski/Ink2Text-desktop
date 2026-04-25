from __future__ import annotations

import json
from pathlib import Path

from app.models import Note


class FileNoteRepository:
    def __init__(self, base_dir: Path | None = None) -> None:
        root_dir = base_dir or Path.cwd() / "app_data"
        self.base_dir = root_dir
        self.notes_dir = self.base_dir / "notes"
        self.notes_dir.mkdir(parents=True, exist_ok=True)

    def list_notes(self) -> list[Note]:
        notes = [self.get_note(path.stem) for path in self.notes_dir.glob("*.json")]
        return sorted(notes, key=lambda note: note.updated_at, reverse=True)

    def get_note(self, note_id: str) -> Note:
        note_path = self._note_path(note_id)
        with note_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return Note.from_dict(payload)

    def save(self, note: Note) -> Note:
        note.touch()
        note_path = self._note_path(note.id)
        with note_path.open("w", encoding="utf-8") as file:
            json.dump(note.to_dict(), file, ensure_ascii=False, indent=2)
            file.write("\n")
        return note

    def _note_path(self, note_id: str) -> Path:
        return self.notes_dir / f"{note_id}.json"

