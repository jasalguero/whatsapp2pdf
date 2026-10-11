"""Core whatsapp2pdf message models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

_DELETED = {"This message was deleted", "You deleted this message", "This message was deleted.", "You deleted this message."}


@dataclass(slots=True)
class Message:
    timestamp: datetime | None
    sender: str | None
    text: str
    media_name: str | None = None
    media_omitted: bool = False
    twelve_hour: bool = False

    @property
    def is_deleted(self) -> bool:
        return self.text.strip() in _DELETED

    @property
    def is_system(self) -> bool:
        return self.sender is None
