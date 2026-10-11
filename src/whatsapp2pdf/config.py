from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from reportlab.lib.pagesizes import A4, A5, A6

FONT_DIR = Path(__file__).parent / "fonts"


class PageSize(str, Enum):
    """Supported ISO page layouts."""

    A4 = "A4"
    A5 = "A5"
    A6 = "A6"

    @property
    def dimensions(self) -> tuple[float, float]:
        return {self.A4: A4, self.A5: A5, self.A6: A6}[self]


# Incoming senders get one slot each, in order of first appearance. Each tint keeps
# 12:1 contrast for message text and at least 4.5:1 for the sender's name color.
SENDER_TINTS = (
    "#CDDFF6", "#F2D8D0", "#E5D5FE", "#F5D1DE", "#C9E2DA",
    "#E9DDCB", "#CAE0E7", "#D8D9F1", "#DCE0CC", "#D7DADE",
)
SENDER_NAME_COLORS = (
    "#165DB5", "#9F4222", "#7736D9", "#AF2859", "#096C4A",
    "#84560F", "#0D6882", "#4C51BF", "#566813", "#4A5568",
)


@dataclass(frozen=True, slots=True)
class Theme:
    """Colors use ReportLab-compatible hex strings."""

    page: str = "#EFEAE2"
    cover: str = "#008069"
    cover_footer: str = "#B9E4DA"
    header: str = "#008069"
    outgoing: str = "#D9FDD3"
    text: str = "#111B21"
    timestamp: str = "#4F5D66"
    muted: str = "#667781"
    running_header: str = "#54656F"
    header_rule: str = "#C9C2B8"
    day_fill: str = "#E1F2FB"
    day_text: str = "#54656F"
    system_fill: str = "#FFF3C4"
    system_text: str = "#54656F"
    attachment: str = "#FFFFFF"
    sender_tints: tuple[str, ...] = SENDER_TINTS
    sender_names: tuple[str, ...] = SENDER_NAME_COLORS

    def sender_slot(self, slot: int) -> tuple[str, str]:
        """(bubble tint, name color) for a sender slot, cycling through the palette."""
        index = slot % min(len(self.sender_tints), len(self.sender_names))
        return self.sender_tints[index], self.sender_names[index]


@dataclass(frozen=True, slots=True)
class LayoutConfig:
    page_size: PageSize | str | tuple[float, float] = PageSize.A4
    margin: float = 36.0
    font_name: str = "NotoSans"
    bold_font_name: str = "NotoSans-Bold"
    font_path: Path | None = None
    bold_font_path: Path | None = None
    emoji_font_path: Path | None = None
    font_size: float = 9.5
    line_height: float = 1.3
    sender_font_size: float = 8.5
    timestamp_font_size: float = 7.0
    big_emoji_size: float = 28.0
    bubble_padding: float = 7.0
    bubble_radius: float = 8.0
    run_gap: float = 1.5
    sender_gap: float = 5.0
    min_bubble_width: float = 60.0
    max_bubble_width_ratio: float = 0.75
    media_max_height: float = 220.0
    image_scale: float = 2.0
    show_cover: bool = True
    show_sender: bool = True
    show_page_numbers: bool = True
    plain: bool = False
    theme: Theme = field(default_factory=Theme)

    def __post_init__(self) -> None:
        if isinstance(self.page_size, str):
            try:
                selected = PageSize(self.page_size.upper()).dimensions
            except ValueError as error:
                raise ValueError("page_size must be A4, A5, A6, or a (width, height) tuple") from error
            object.__setattr__(self, "page_size", selected)
        elif len(self.page_size) != 2 or any(value <= 0 for value in self.page_size):
            raise ValueError("page_size dimensions must be greater than zero")
        if not 0.3 <= self.max_bubble_width_ratio <= 0.95:
            raise ValueError("max_bubble_width_ratio must be between 0.3 and 0.95")
        for name in ("margin", "font_size", "bubble_padding", "media_max_height"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be greater than zero")

    @property
    def page_color(self) -> str:
        return "#FFFFFF" if self.plain else self.theme.page
