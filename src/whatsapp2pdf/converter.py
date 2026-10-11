"""Public conversion entry point for whatsapp2pdf."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import LayoutConfig
from .parser import parse_text
from .renderer import PDFRenderer
from .source import ExportSource
from .stats import ChatStats


@dataclass(frozen=True, slots=True)
class ConversionResult:
    output: Path
    messages: int


def default_title(source: str | Path) -> str:
    """'WhatsApp Chat - Ana.zip' or 'WhatsApp Chat with Ana.txt' -> 'Ana'."""
    stem = Path(source).stem
    if stem.lower() in {"_chat", "chat"}:
        stem = Path(source).resolve().parent.name or stem
    cleaned = re.sub(r"(?i)^whatsapp\s+chat\s*(?:-|with)?\s*", "", stem).strip(" -_")
    return cleaned or "WhatsApp chat"


def convert(
    source: str | Path,
    output: str | Path,
    *,
    outgoing: str | set[str] | tuple[str, ...] = (),
    title: str | None = None,
    config: LayoutConfig | None = None,
    day_first: bool = True,
    chat_member: str | None = None,
) -> ConversionResult:
    """Convert a .txt export or WhatsApp .zip export into a PDF."""
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    senders = {outgoing} if isinstance(outgoing, str) else set(outgoing)
    layout = config or LayoutConfig()
    # A cheap text-only pre-pass gives the cover its totals and fixes sender colors up front.
    with ExportSource(source, chat_member=chat_member) as export:
        stats = ChatStats.collect(parse_text(export.chat, day_first=day_first))
    with ExportSource(source, chat_member=chat_member) as export:
        messages = parse_text(export.chat, day_first=day_first)
        renderer = PDFRenderer(destination, layout, title or default_title(source), senders, stats)
        count = renderer.render(messages, export)
    return ConversionResult(destination, count)
