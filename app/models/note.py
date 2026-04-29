from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class Note:
    id: str
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    image_paths: list[str] = field(default_factory=list)

    @classmethod
    def create_empty(cls) -> "Note":
        now = _utc_now()
        return cls(
            id=uuid4().hex,
            title="Nowa notatka",
            content="",
            created_at=now,
            updated_at=now,
            image_paths=[],
        )

    @property
    def display_title(self) -> str:
        title = self.title.strip()
        return title if title else "Bez tytulu"

    def touch(self) -> None:
        self.updated_at = _utc_now()

    def to_dict(self) -> dict[str, str | list[str]]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "image_paths": self.image_paths,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | list[str]]) -> "Note":
        return cls(
            id=data["id"],
            title=data.get("title", ""),
            content=data.get("content", ""),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            image_paths=list(data.get("image_paths", [])),
        )
