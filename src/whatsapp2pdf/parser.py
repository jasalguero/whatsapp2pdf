"""Streaming parsers for WhatsApp chat exports."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, Iterator, TextIO

from .models import Message

# Android: 31/12/23, 23:59 - Name: text
# iOS: [31/12/23, 23:59:01] Name: text
_LINE = re.compile(
    r"^(?:\[)?(?P<date>\d{1,4}[/.\-]\d{1,2}[/.\-]\d{1,4}),?\s+"
    r"(?P<time>\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)(?:\])?\s+(?:-\s+)?"
    r"(?P<body>.*)$"
)
_MEDIA = re.compile(
    r"(?:<attached:\s*(?P<ios>[^>]+)>|(?P<android>[^\n]+?)\s+\((?:file )?attached\))",
    re.IGNORECASE,
)
# iOS attributes these notices to a participant; they read better as system messages.
_SYSTEM_NOTICES = (
    "messages and calls are end-to-end encrypted",
    "messages to this group are now secured",
)
# Exports made "without media" leave a placeholder instead of a filename.
_OMITTED = re.compile(r"^<\s*media omitted\s*>$|^(image|video|audio|sticker|gif|document) omitted$", re.IGNORECASE)
_INVISIBLE = str.maketrans({
    "\u200e": None, "\u200f": None, "\u202a": None, "\u202b": None,
    "\u202c": None, "\u202d": None, "\u202e": None, "\u2066": None,
    "\u2067": None, "\u2068": None, "\u2069": None, "\ufeff": None,
    "\u202f": " ", "\u00a0": " ",
})
_FORMATS = (
    "%d/%m/%y %H:%M", "%d/%m/%Y %H:%M", "%m/%d/%y %H:%M", "%m/%d/%Y %H:%M",
    "%d/%m/%y %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S",
    "%d/%m/%y %I:%M %p", "%m/%d/%y %I:%M %p", "%d/%m/%Y %I:%M %p", "%m/%d/%Y %I:%M %p",
    "%d/%m/%y %I:%M:%S %p", "%m/%d/%y %I:%M:%S %p", "%d/%m/%Y %I:%M:%S %p", "%m/%d/%Y %I:%M:%S %p",
    "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S",
)


def _timestamp(date: str, time: str, *, day_first: bool) -> datetime | None:
    candidates = list(_FORMATS)
    if not day_first:
        candidates.sort(key=lambda value: 0 if value.startswith("%m") else 1)
    for fmt in candidates:
        try:
            return datetime.strptime(f"{date} {time.strip().upper()}", fmt)
        except ValueError:
            pass
    return None


def _message(match: re.Match[str], *, day_first: bool) -> Message:
    body = match.group("body")
    sender, separator, text = body.partition(": ")
    if not separator or text.casefold().startswith(_SYSTEM_NOTICES):
        sender, text = None, text if separator else body
    # Guard the regex: its lazy Android branch is quadratic on very long messages.
    media_match = _MEDIA.search(text) if "attached" in text.casefold() else None
    media_name = None
    if media_match:
        media_name = (media_match.group("ios") or media_match.group("android")).strip()
        text = (text[: media_match.start()] + text[media_match.end() :]).strip()
    omitted = bool(_OMITTED.match(text.strip()))
    if omitted:
        text = ""
    return Message(
        timestamp=_timestamp(match.group("date"), match.group("time"), day_first=day_first),
        sender=sender,
        text=text,
        media_name=media_name,
        media_omitted=omitted,
        twelve_hour=bool(re.search(r"[APap][Mm]", match.group("time"))),
    )


def _normalize_export_line(value: str) -> str:
    """Remove WhatsApp's bidi marks and normalize localized AM/PM forms."""
    value = value.translate(_INVISIBLE)
    return re.sub(r"(?i)\b([ap])\s*\.\s*m\s*\.", r"\1m", value)


# Exports are untrusted: bound how much of one message (or one physical line) is held in memory.
MAX_MESSAGE_CHARS = 1_000_000
READ_CHUNK_CHARS = 64 * 1024
TRUNCATED_MARK = "… (truncated)"


def parse_chat(lines: Iterable[str], *, day_first: bool = True) -> Iterator[Message]:
    """Parse incrementally; only the current message is retained in memory.

    ``lines`` may also yield pieces of an overlong line: a piece without a trailing
    newline is joined to the next one instead of starting a new line.
    """
    current: Message | None = None
    truncated = False
    at_line_start = True

    def finish(message: Message) -> Message:
        if truncated:
            message.text = message.text[:MAX_MESSAGE_CHARS] + TRUNCATED_MARK
        return message

    for raw_line in lines:
        starts_line = at_line_start
        at_line_start = raw_line.endswith(("\n", "\r"))
        line = _normalize_export_line(raw_line.rstrip("\r\n"))
        match = _LINE.match(line) if starts_line else None
        if match:
            if current is not None:
                yield finish(current)
            current = _message(match, day_first=day_first)
            truncated = False
        elif current is not None:
            if truncated:
                continue
            current.text += ("\n" if starts_line else "") + line
            if len(current.text) > MAX_MESSAGE_CHARS:
                truncated = True
        elif line:
            current = Message(None, None, line)
    if current is not None:
        yield finish(current)


def parse_text(stream: TextIO, *, day_first: bool = True) -> Iterator[Message]:
    chunks = iter(lambda: stream.readline(READ_CHUNK_CHARS), "")
    return parse_chat(chunks, day_first=day_first)
