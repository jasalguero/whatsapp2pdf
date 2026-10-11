"""Cheap pre-pass over the chat text for the cover page and sender colors."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

from .models import Message
from .source import ExportSource


@dataclass(slots=True)
class ChatStats:
    first: datetime | None = None
    last: datetime | None = None
    messages: int = 0
    photos: int = 0
    files: int = 0
    # Insertion order is the order of first appearance.
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def days(self) -> int:
        if self.first is None or self.last is None:
            return 0
        return (self.last.date() - self.first.date()).days + 1

    @classmethod
    def collect(cls, messages: Iterable[Message]) -> "ChatStats":
        stats = cls()
        for message in messages:
            if message.timestamp is not None:
                stats.first = stats.first or message.timestamp
                stats.last = message.timestamp
            if message.is_system:
                continue
            stats.messages += 1
            stats.counts[message.sender] = stats.counts.get(message.sender, 0) + 1
            if message.media_name and ExportSource.media_kind(message.media_name) == "image":
                stats.photos += 1
            elif message.media_name or message.media_omitted:
                stats.files += 1
        return stats
