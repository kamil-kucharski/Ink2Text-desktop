from app.models import Note


def test_create_empty_note_has_defaults() -> None:
    note = Note.create_empty()

    assert note.id
    assert note.title == "Nowa notatka"
    assert note.content == ""
    assert note.image_paths == []
    assert note.created_at == note.updated_at


def test_note_serialization_roundtrip() -> None:
    note = Note.create_empty()
    note.title = "Test"
    note.content = "Przykladowa tresc"
    note.image_paths = ["uploads/test/image.png"]

    restored = Note.from_dict(note.to_dict())

    assert restored.id == note.id
    assert restored.title == "Test"
    assert restored.content == "Przykladowa tresc"
    assert restored.image_paths == ["uploads/test/image.png"]
