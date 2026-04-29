from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

from app.models import Note


class FileNoteRepository:
    def __init__(self, base_dir: Path | None = None) -> None:
        root_dir = base_dir or Path.cwd() / "app_data"
        self.base_dir = root_dir
        self.notes_dir = self.base_dir / "notes"
        self.uploads_dir = self.base_dir / "uploads"
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

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

    def import_images(self, note: Note, source_paths: list[str]) -> list[str]:
        note_uploads_dir = self.uploads_dir / note.id
        note_uploads_dir.mkdir(parents=True, exist_ok=True)

        imported_paths: list[str] = []
        for raw_path in source_paths:
            source_path = Path(raw_path)
            if not source_path.is_file():
                continue

            suffix = source_path.suffix.lower() or ".img"
            destination_name = f"{uuid4().hex}{suffix}"
            destination_path = note_uploads_dir / destination_name
            shutil.copy2(source_path, destination_path)

            relative_path = destination_path.relative_to(self.base_dir).as_posix()
            note.image_paths.append(relative_path)
            imported_paths.append(relative_path)

        if imported_paths:
            self.save(note)

        return imported_paths

    def remove_image(self, note: Note, relative_path: str) -> None:
        if relative_path not in note.image_paths:
            return

        note.image_paths.remove(relative_path)
        absolute_path = self.resolve_image_path(relative_path)
        if absolute_path.exists():
            absolute_path.unlink()
        self.save(note)

    def resolve_image_path(self, relative_path: str) -> Path:
        return self.base_dir / Path(relative_path)

    def _note_path(self, note_id: str) -> Path:
        return self.notes_dir / f"{note_id}.json"
