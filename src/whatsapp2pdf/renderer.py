from __future__ import annotations

import io
import warnings
from collections.abc import Callable, Iterable
from datetime import date, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from .config import FONT_DIR, LayoutConfig
from .models import Message
from .source import ExportSource
from .stats import ChatStats

_CONTINUATION = (0xFE0E, 0xFE0F, 0x200D, 0x20E3)
# Pillow picks a decoder by file content, not extension; never let a disguised file reach
# plugins such as EPS, which shells out to Ghostscript.
SAFE_IMAGE_FORMATS = ("JPEG", "PNG", "WEBP", "GIF", "BMP", "TIFF")


def _wrap(text: str, width: float, measure: Callable[[str], float]) -> list[str]:
    result: list[str] = []
    for paragraph in (text or "").splitlines() or [""]:
        words = paragraph.split()
        if not words:
            result.append("")
            continue
        line = words.pop(0)
        for word in words:
            candidate = f"{line} {word}"
            if measure(candidate) <= width:
                line = candidate
            else:
                if measure(line) > width:
                    line = _split_long(line, width, measure, result)
                result.append(line)
                line = word
        if measure(line) > width:
            line = _split_long(line, width, measure, result)
        result.append(line)
    return result


def _split_long(value: str, width: float, measure: Callable[[str], float], output: list[str]) -> str:
    chunk = ""
    for char in value:
        if chunk and measure(chunk + char) > width:
            output.append(chunk)
            chunk = char
        else:
            chunk += char
    return chunk


def _long_date(value: date) -> str:
    return f"{value:%A}, {value.day} {value:%B %Y}"


def _short_date(value: date) -> str:
    return f"{value.day} {value:%B %Y}"


def _clock(value: datetime, twelve_hour: bool) -> str:
    if twelve_hour:
        return f"{value.hour % 12 or 12}:{value:%M} {'am' if value.hour < 12 else 'pm'}"
    return f"{value:%H:%M}"


class PDFRenderer:
    def __init__(
        self,
        output: str | Path,
        config: LayoutConfig,
        title: str,
        outgoing: set[str] | None = None,
        stats: ChatStats | None = None,
    ) -> None:
        self.config = config
        self.theme = config.theme
        self.title = title
        self.outgoing = outgoing or set()
        self.stats = stats or ChatStats()
        self.canvas = Canvas(str(output), pagesize=config.page_size, pageCompression=1)
        self.canvas.setTitle(title)
        self.canvas.setCreator("whatsapp2pdf")
        self.width, self.height = config.page_size
        self.y = 0.0
        self._page_open = False
        self._page_has_content = False
        self._emoji_font_path = config.emoji_font_path or self._find_emoji_font()
        self._emoji_font_obj: ImageFont.FreeTypeFont | None | bool = False
        self._emoji_cache: dict[str, tuple[ImageReader, float] | None] = {}
        self._register_fonts()
        incoming = [name for name in self.stats.counts if name not in self.outgoing]
        self._slots: dict[str, int] = {name: index for index, name in enumerate(incoming)}
        # Names add nothing in a one-to-one chat: the side already says who spoke.
        self._group = len(incoming) > 1

    # ---------- setup ----------

    @staticmethod
    def _find_emoji_font() -> Path | None:
        candidates = (
            Path("/System/Library/Fonts/Apple Color Emoji.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"),
            Path("/usr/share/fonts/noto/NotoColorEmoji.ttf"),
            Path("C:/Windows/Fonts/seguiemj.ttf"),
        )
        return next((path for path in candidates if path.is_file()), None)

    def _register_fonts(self) -> None:
        cfg = self.config
        regular = cfg.font_path or (FONT_DIR / "NotoSans-Regular.ttf" if cfg.font_name == "NotoSans" else None)
        bold = cfg.bold_font_path or (FONT_DIR / "NotoSans-Bold.ttf" if cfg.bold_font_name == "NotoSans-Bold" else None)
        if regular is not None:
            name = "WAPDFCustom" if cfg.font_path else "NotoSans"
            pdfmetrics.registerFont(TTFont(name, str(regular)))
            object.__setattr__(cfg, "font_name", name)
        if bold is not None:
            name = "WAPDFCustomBold" if cfg.bold_font_path else "NotoSans-Bold"
            pdfmetrics.registerFont(TTFont(name, str(bold)))
            object.__setattr__(cfg, "bold_font_name", name)

    # ---------- pages ----------

    def _new_page(self, day: date | None) -> None:
        cfg, c = self.config, self.canvas
        if self._page_open:
            self._footer()
            c.showPage()
        self._page_open = True
        self._page_has_content = False
        c.setFillColor(HexColor(cfg.page_color))
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        c.setFillColor(HexColor(self.theme.running_header))
        c.setFont(cfg.bold_font_name, 8)
        c.drawString(cfg.margin, self.height - 28, self._fit(self.title, cfg.bold_font_name, 8, self.width * 0.6))
        if day is not None:
            c.setFont(cfg.font_name, 8)
            c.drawRightString(self.width - cfg.margin, self.height - 28, _short_date(day))
        c.setStrokeColor(HexColor(self.theme.header_rule))
        c.setLineWidth(0.5)
        c.line(cfg.margin, self.height - 34, self.width - cfg.margin, self.height - 34)
        self.y = self.height - 50

    def _footer(self) -> None:
        if self.config.show_page_numbers:
            self.canvas.setFillColor(HexColor(self.theme.muted))
            self.canvas.setFont(self.config.font_name, 7)
            self.canvas.drawCentredString(self.width / 2, 20, str(self.canvas.getPageNumber()))

    def _bottom(self) -> float:
        return self.config.margin

    def _ensure_room(self, height: float, day: date | None) -> bool:
        """Start a new page when needed. Returns True if a page was started."""
        fresh_page = self.height - 50 - self._bottom()
        if self._page_open and height > fresh_page and self.y - self._bottom() > 80:
            return False  # too tall for any page: start it here and let it continue
        if not self._page_open or (self._page_has_content and self.y - height < self._bottom()):
            self._new_page(day)
            return True
        return False

    def _fit(self, text: str, font: str, size: float, width: float) -> str:
        if pdfmetrics.stringWidth(text, font, size) <= width:
            return text
        while text and pdfmetrics.stringWidth(text + "…", font, size) > width:
            text = text[:-1]
        return text + "…"

    # ---------- render ----------

    def render(self, messages: Iterable[Message], source: ExportSource) -> int:
        if self.config.show_cover:
            self._draw_cover()
        count = 0
        day: date | None = None
        previous: str | None = None  # sender of the previous bubble in this run
        for message in messages:
            message_day = message.timestamp.date() if message.timestamp else day
            if message_day is not None and message_day != day:
                day = message_day
                self._draw_day_pill(day)
                previous = None
            if message.is_system:
                self._draw_system(message, day)
                previous = None
            else:
                self._draw_message(message, source, day, first_of_run=message.sender != previous)
                previous = message.sender
            count += 1
        if not self._page_open:
            self._new_page(day)
        self._footer()
        self.canvas.save()
        return count

    # ---------- pills ----------

    def _pill_lines(self, text: str, size: float) -> list[str]:
        max_width = (self.width - self.config.margin * 2) * self.config.max_bubble_width_ratio - 12
        return _wrap(text, max_width, lambda value: self._rich_width(value, self.config.font_name, size))

    def _pill_height(self, lines: list[str], size: float) -> float:
        return len(lines) * (size * 1.3) + 6.5

    def _pill(self, text: str, fill: str, color: str, size: float, gap_before: float = 8) -> None:
        cfg, c = self.config, self.canvas
        lines = self._pill_lines(text, size)
        lead = size * 1.3
        height = self._pill_height(lines, size)
        width = max(self._rich_width(line, cfg.font_name, size) for line in lines) + 12
        self.y -= gap_before
        top = self.y
        c.setFillColor(HexColor(fill))
        c.roundRect((self.width - width) / 2, top - height, width, height, 5, fill=1, stroke=0)
        c.setFillColor(HexColor(color))
        baseline = top - 3 - size
        for line in lines:
            self._draw_rich((self.width - self._rich_width(line, cfg.font_name, size)) / 2, baseline, line, cfg.font_name, size)
            baseline -= lead
        self.y = top - height
        self._page_has_content = True

    def _draw_day_pill(self, day: date) -> None:
        text = _long_date(day)
        needed = 8 + self._pill_height([text], 8) + 8 + 40  # keep the pill with at least one bubble
        self._ensure_room(needed, day)
        self._pill(text, self.theme.day_fill, self.theme.day_text, 8, gap_before=8 if self._page_has_content else 0)
        self.y -= 8

    def _draw_system(self, message: Message, day: date | None) -> None:
        lines = self._pill_lines(message.text, 7.5)
        needed = self._pill_height(lines, 7.5) + 7
        if self._ensure_room(needed, day):
            self._begin_after_break(day)
        self._pill(message.text, self.theme.system_fill, self.theme.system_text, 7.5, gap_before=0)
        self.y -= 7

    def _begin_after_break(self, day: date | None) -> None:
        """Every chat page opens with its date so a reader landing anywhere knows when it is."""
        if day is not None:
            self._pill(_long_date(day), self.theme.day_fill, self.theme.day_text, 8, gap_before=0)
            self.y -= 8

    # ---------- bubbles ----------

    def _colors(self, sender: str | None, is_outgoing: bool) -> tuple[str, str]:
        if is_outgoing:
            return self.theme.outgoing, self.theme.header
        if sender not in self._slots:
            self._slots[sender] = len(self._slots)
        return self.theme.sender_slot(self._slots[sender])

    def _is_big_emoji(self, message: Message) -> bool:
        text = message.text.strip()
        if not text or message.media_name or message.media_omitted:
            return False
        segments = list(self._rich_segments(text))
        if any(not is_emoji and value.strip() for is_emoji, value in segments):
            return False
        visible = [ch for ch in text if not ch.isspace() and ord(ch) not in _CONTINUATION and not 0x1F3FB <= ord(ch) <= 0x1F3FF]
        return 0 < len(visible) <= 3

    def _draw_message(self, message: Message, source: ExportSource, day: date | None, *, first_of_run: bool) -> None:
        if self._is_big_emoji(message) and self._emoji_font() is not None:
            return self._draw_big_emoji(message, day, first_of_run=first_of_run)
        return self._draw_bubble(message, source, day, first_of_run=first_of_run)

    def _stamp(self, message: Message) -> str:
        return _clock(message.timestamp, message.twelve_hour) if message.timestamp else ""

    def _draw_big_emoji(self, message: Message, day: date | None, *, first_of_run: bool) -> None:
        cfg, c = self.config, self.canvas
        is_outgoing = message.sender in self.outgoing
        _, name_color = self._colors(message.sender, is_outgoing)
        size = cfg.big_emoji_size
        text = "".join(value for is_emoji, value in self._rich_segments(message.text.strip()) if is_emoji)
        glyph = self._emoji_image(text)
        width = size * glyph[1] if glyph else size
        stamp = self._stamp(message)
        stamp_w = pdfmetrics.stringWidth(stamp, cfg.font_name, cfg.timestamp_font_size) + 4
        show_name = first_of_run and not is_outgoing and self._group and cfg.show_sender
        height = size + 4 + (12 if show_name else 0)
        gap = cfg.sender_gap if first_of_run else cfg.run_gap
        if self._ensure_room(height + gap, day):
            self._begin_after_break(day)
        elif self._page_has_content:
            self.y -= gap
        total_w = width + stamp_w
        x = self.width - cfg.margin - total_w if is_outgoing else cfg.margin
        if show_name:
            c.setFillColor(HexColor(name_color))
            self._draw_rich(x, self.y - 9, message.sender or "", cfg.bold_font_name, cfg.sender_font_size)
            self.y -= 12
        if glyph:
            c.drawImage(glyph[0], x, self.y - size, width, size, mask="auto")
        c.setFillColor(HexColor(self.theme.timestamp))
        c.setFont(cfg.font_name, cfg.timestamp_font_size)
        c.drawString(x + width + 4, self.y - size + 2, stamp)
        self.y -= size + 4
        self._page_has_content = True

    def _draw_bubble(
        self,
        message: Message,
        source: ExportSource,
        day: date | None,
        *,
        first_of_run: bool,
        lines: list[str] | None = None,
        continuation: bool = False,
    ) -> None:
        cfg, c, theme = self.config, self.canvas, self.theme
        is_outgoing = message.sender in self.outgoing
        fill, name_color = self._colors(message.sender, is_outgoing)
        pad = cfg.bubble_padding
        fs = cfg.font_size
        lead = fs * cfg.line_height
        max_w = (self.width - cfg.margin * 2) * cfg.max_bubble_width_ratio
        inner_max = max_w - pad * 2
        measure = lambda value: self._rich_width(value, cfg.font_name, fs)  # noqa: E731
        if lines is None:
            lines = _wrap(message.text, inner_max, measure) if message.text.strip() else []
        show_name = first_of_run and not is_outgoing and self._group and cfg.show_sender and not continuation
        name_h = 12 if show_name else 0
        media = None if continuation else (self._load_image(source, message.media_name, max_w - 6) if message.media_name else None)
        has_card = not continuation and not media and bool(message.media_name or message.media_omitted)
        card_label = message.media_name or "Media not included in export"
        stamp = self._stamp(message)
        stamp_w = pdfmetrics.stringWidth(stamp, cfg.font_name, cfg.timestamp_font_size) + 6
        gap = cfg.sender_gap if first_of_run else cfg.run_gap

        def text_h(count: int) -> float:
            return count * lead - (lead - fs) if count else 0.0

        def layout(chunk: list[str], stamp_text: str) -> tuple[float, float, bool]:
            last_w = measure(chunk[-1]) if chunk else 0.0
            stamp_inline = bool(chunk) and last_w + stamp_w + 4 <= inner_max
            over_photo = bool(media) and not chunk
            widest = max((measure(line) for line in chunk), default=0.0)
            width = max(
                cfg.min_bubble_width,
                widest + pad * 2,
                (pdfmetrics.stringWidth(message.sender or "", cfg.bold_font_name, cfg.sender_font_size) + pad * 2) if show_name else 0,
                (last_w + stamp_w + 4 + pad * 2) if stamp_inline else 0,
                (media[1] + 6) if media else 0,
                min(max_w, pdfmetrics.stringWidth(card_label, cfg.bold_font_name, fs) + 42 + pad * 2) if has_card else 0,
            )
            width = min(width, max_w)
            stamp_line = 0 if (stamp_inline or over_photo or not stamp_text) else 9
            # Mirrors the drawing steps in _draw_bubble below.
            height = pad + name_h if show_name else 0.0
            if media:
                height += (0 if show_name else 3) + media[2] + 3
            elif has_card:
                height += (0 if show_name else pad) + 34
            elif not show_name:
                height += pad
            if chunk:
                height += (pad - 3 if media else 0) + text_h(len(chunk)) + stamp_line + pad
            elif not media:
                height += stamp_line + pad
            return width, height, stamp_inline

        _, height, _ = layout(lines, stamp)
        if self._ensure_room(height + gap, day):
            self._begin_after_break(day)
            gap = 0
        elif not self._page_has_content:
            gap = 0
        available = self.y - gap - self._bottom()
        tail: list[str] = []
        if height > available and len(lines) > 1:
            # Pathologically long message: draw what fits, continue in a new bubble.
            fixed = height - text_h(len(lines))
            fit = max(1, int((available - fixed + (lead - fs)) / lead))
            lines, tail = lines[:fit], lines[fit:]
        shown_stamp = "continued" if tail else stamp
        if tail:
            stamp_w = pdfmetrics.stringWidth(shown_stamp, cfg.font_name, cfg.timestamp_font_size) + 6
        width, height, stamp_inline = layout(lines, shown_stamp)

        self.y -= gap
        top = self.y
        x = self.width - cfg.margin - width if is_outgoing else cfg.margin
        c.setFillColor(HexColor(fill))
        c.roundRect(x, top - height, width, height, cfg.bubble_radius, fill=1, stroke=0)
        if first_of_run and not continuation:
            path = c.beginPath()
            if is_outgoing:
                path.moveTo(x + width - 8, top)
                path.lineTo(x + width + 6, top)
                path.lineTo(x + width, top - 9)
            else:
                path.moveTo(x + 8, top)
                path.lineTo(x - 6, top)
                path.lineTo(x, top - 9)
            path.close()
            c.drawPath(path, fill=1, stroke=0)

        cursor = top
        if show_name:
            c.setFillColor(HexColor(name_color))
            self._draw_rich(x + pad, top - pad - cfg.sender_font_size, message.sender or "", cfg.bold_font_name, cfg.sender_font_size)
            cursor -= pad + name_h
        if media:
            reader, media_w, media_height = media
            cursor -= 0 if show_name else 3
            c.drawImage(reader, x + 3, cursor - media_height, media_w, media_height, mask="auto")
            if not lines and shown_stamp:
                self._photo_stamp(x + 3 + media_w, cursor - media_height, shown_stamp)
            cursor -= media_height + 3
        elif has_card:
            cursor -= 0 if show_name else pad
            c.saveState()
            c.setFillColor(HexColor(theme.attachment))
            c.setFillAlpha(0.65)
            c.roundRect(x + pad, cursor - 28, width - pad * 2, 28, 4, fill=1, stroke=0)
            c.restoreState()
            kind = source.media_kind(message.media_name) if message.media_name else "document"
            self._draw_attachment_icon(x + pad + 14, cursor - 14, kind)
            c.setFillColor(HexColor(theme.text if message.media_name else theme.timestamp))
            label = self._fit(card_label, cfg.bold_font_name, fs, width - pad * 2 - 40)
            c.setFont(cfg.bold_font_name, fs)
            c.drawString(x + pad + 30, cursor - 17.5, label)
            cursor -= 34
        elif not show_name:
            cursor -= pad
        if lines and media:
            cursor -= pad - 3
        c.setFillColor(HexColor(theme.timestamp if message.is_deleted else theme.text))
        for index, line in enumerate(lines):
            baseline = cursor - fs - index * lead
            self._draw_rich(x + pad, baseline, line, cfg.font_name, fs)
        if shown_stamp and (lines or not media):
            c.setFillColor(HexColor(theme.timestamp))
            c.setFont(cfg.font_name, cfg.timestamp_font_size)
            c.drawRightString(x + width - pad, top - height + pad - 1.5, shown_stamp)
        self.y = top - height
        self._page_has_content = True
        if tail:
            rest = Message(message.timestamp, message.sender, "", twelve_hour=message.twelve_hour)
            self._draw_bubble(rest, source, day, first_of_run=False, lines=tail, continuation=True)

    def _photo_stamp(self, right: float, bottom: float, stamp: str) -> None:
        cfg, c = self.config, self.canvas
        width = pdfmetrics.stringWidth(stamp, cfg.font_name, cfg.timestamp_font_size) + 8
        c.saveState()
        c.setFillColorRGB(0, 0, 0)
        c.setFillAlpha(0.35)
        c.roundRect(right - width - 4, bottom + 3, width, cfg.timestamp_font_size + 5, 4, fill=1, stroke=0)
        c.restoreState()
        c.setFillColorRGB(1, 1, 1)
        c.setFont(cfg.font_name, cfg.timestamp_font_size)
        c.drawRightString(right - 8, bottom + 6, stamp)

    def _load_image(self, source: ExportSource, name: str | None, max_width: float):
        if not name or source.media_kind(name) != "image":
            return None
        stream = source.open_media(name)
        if stream is None:
            return None
        scale = max(1.0, self.config.image_scale)
        box = (int(max_width * scale), int(self.config.media_max_height * scale))
        try:
            # Oversized images ("decompression bombs") fall back to an attachment card.
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with stream, Image.open(stream, formats=SAFE_IMAGE_FORMATS) as original:
                    original.draft("RGB", box)  # JPEG: decode at reduced size
                    image = ImageOps.exif_transpose(original)
                    image.thumbnail(box)
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGB")
                buffer = io.BytesIO()
                if image.mode == "RGBA":
                    image.save(buffer, "PNG", optimize=True)
                else:
                    image.save(buffer, "JPEG", quality=85, optimize=True)
                buffer.seek(0)
                return ImageReader(buffer), image.width / scale, image.height / scale
        except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            return None

    # ---------- cover ----------

    def _draw_cover(self) -> None:
        cfg, c, theme, stats = self.config, self.canvas, self.theme, self.stats
        w, h = self.width, self.height
        k = w / 595.28  # the cover is specified for A4; scale it for smaller pages
        left, right = 72 * k, w - 72 * k
        c.setFillColor(HexColor(theme.cover))
        c.rect(0, 0, w, h, fill=1, stroke=0)
        c.setFillColorRGB(1, 1, 1)
        c.setStrokeColorRGB(1, 1, 1)
        y = h - 150 * k
        c.setFont(cfg.bold_font_name, 9 * k)
        c.drawString(left, y, "   ".join(" ".join(word) for word in "WHATSAPP CHAT".split()))
        y -= 44 * k
        title_size = 30 * k
        while title_size > 14 * k and pdfmetrics.stringWidth(self.title, cfg.bold_font_name, title_size) > right - left:
            title_size -= 1
        c.setFont(cfg.bold_font_name, title_size)
        c.drawString(left, y, self._fit(self.title, cfg.bold_font_name, title_size, right - left))
        if stats.first and stats.last:
            y -= 28 * k
            c.setFont(cfg.font_name, 13 * k)
            span = _short_date(stats.first.date())
            if stats.last.date() != stats.first.date():
                span += f" to {_short_date(stats.last.date())}"
            c.drawString(left, y, span)
        y -= 22 * k
        c.setLineWidth(0.6)
        c.line(left, y, right, y)

        y -= 40 * k
        c.setFont(cfg.bold_font_name, 9 * k)
        c.drawString(left, y, " ".join("PARTICIPANTS"))
        y -= 30 * k
        rows = self._cover_participants()
        row_h = 28 * k
        max_rows = max(1, int((y - 220 * k) / row_h))
        limit = 12 if len(rows) <= 12 else 11
        limit = min(limit, max_rows if len(rows) > max_rows else len(rows))
        for name, count, color, is_me in rows[:limit]:
            c.setFillColorRGB(1, 1, 1)
            c.circle(left + 6 * k, y + 4 * k, 7 * k, fill=1, stroke=0)
            c.setFillColor(HexColor(color))
            c.circle(left + 6 * k, y + 4 * k, 5 * k, fill=1, stroke=0)
            c.setFillColorRGB(1, 1, 1)
            label = name + ("  (you)" if is_me else "")
            self._draw_rich(left + 24 * k, y, self._fit(label, cfg.font_name, 13 * k, (right - left) * 0.6), cfg.font_name, 13 * k)
            c.setFont(cfg.font_name, 11 * k)
            c.drawRightString(right, y, f"{count:,} message{'s' if count != 1 else ''}")
            y -= row_h
        if len(rows) > limit:
            c.setFont(cfg.font_name, 11 * k)
            c.drawString(left + 24 * k, y, f"and {len(rows) - limit} others")

        y = 150 * k
        c.line(left, y + 34 * k, right, y + 34 * k)
        totals = [
            (stats.messages, "messages"), (stats.photos, "photos"),
            (stats.files, "other files"), (stats.days, "days"),
        ]
        column = (right - left) / 4
        for index, (number, label) in enumerate(totals):
            c.setFont(cfg.bold_font_name, 20 * k)
            c.drawString(left + index * column, y, f"{number:,}")
            c.setFont(cfg.font_name, 9 * k)
            c.drawString(left + index * column, y - 15 * k, label)
        c.setFillColor(HexColor(theme.cover_footer))
        c.setFont(cfg.font_name, 8 * k)
        today = date.today()
        c.drawString(left, 60 * k, f"Exported with whatsapp2pdf on {today.day} {today:%B %Y}")
        c.showPage()

    def _cover_participants(self) -> list[tuple[str, int, str, bool]]:
        rows: list[tuple[str, int, str, bool]] = []
        mine_name, mine_count = None, 0
        for name, count in self.stats.counts.items():
            if name in self.outgoing:
                mine_name = mine_name or name
                mine_count += count
            else:
                rows.append((name, count, self._colors(name, False)[1], False))
        if mine_name is not None:
            _, color = self.theme.sender_slot(len(self._slots))
            rows.append((mine_name, mine_count, color, True))
        return sorted(rows, key=lambda row: row[1], reverse=True)

    # ---------- text and emoji ----------

    @staticmethod
    def _is_emoji_character(char: str) -> bool:
        value = ord(char)
        return (
            0x1F000 <= value <= 0x1FAFF
            or 0x2600 <= value <= 0x27BF
            or value in (0x00A9, 0x00AE, 0x203C, 0x2049, 0x2122, 0x2139, 0x2B50, 0x2B55, 0x2B1B, 0x2B1C)
        )

    def _rich_segments(self, line: str):
        text = ""
        emoji = ""
        joining = False
        for char in line:
            value = ord(char)
            continuation = value in _CONTINUATION or 0x1F3FB <= value <= 0x1F3FF
            if self._is_emoji_character(char) or (emoji and continuation) or joining:
                if text:
                    yield False, text
                    text = ""
                emoji += char
                joining = value == 0x200D
            elif continuation:
                continue
            else:
                if emoji:
                    yield True, emoji
                    emoji = ""
                text += char
                joining = False
        if emoji:
            yield True, emoji
        if text:
            yield False, text

    def _emoji_font(self):
        """Color emoji fonts are bitmap strikes that only open at the sizes they ship.

        Apple Color Emoji includes 160px; Noto Color Emoji only 109px.
        """
        if self._emoji_font_obj is False:
            self._emoji_font_obj = None
            if self._emoji_font_path is not None:
                for size in (109, 160, 96, 64):
                    try:
                        self._emoji_font_obj = ImageFont.truetype(str(self._emoji_font_path), size)
                        break
                    except OSError:
                        continue
        return self._emoji_font_obj

    def _emoji_image(self, value: str):
        if value in self._emoji_cache:
            return self._emoji_cache[value]
        result = None
        font = self._emoji_font()
        if font is not None:
            try:
                em = font.size
                canvas = Image.new("RGBA", (max(2 * em, int(em * 1.4) * len(value)), int(em * 1.6)), (0, 0, 0, 0))
                ImageDraw.Draw(canvas).text((4, 4), value, font=font, embedded_color=True)
                bbox = canvas.getbbox()
                if bbox is not None:
                    glyph = canvas.crop(bbox)
                    buffer = io.BytesIO()
                    glyph.save(buffer, "PNG")
                    buffer.seek(0)
                    result = (ImageReader(buffer), glyph.width / glyph.height)
            except (OSError, ValueError):
                result = None
        self._emoji_cache[value] = result
        return result

    def _rich_width(self, line: str, font: str, size: float) -> float:
        total = 0.0
        for is_emoji, value in self._rich_segments(line):
            if not is_emoji:
                total += pdfmetrics.stringWidth(value, font, size)
                continue
            glyph = self._emoji_image(value)
            if glyph is None:
                total += pdfmetrics.stringWidth("[emoji]", font, size)
            else:
                total += (size + 1) * glyph[1] + 0.5
        return total

    def _draw_rich(self, x: float, baseline: float, line: str, font: str, size: float) -> None:
        c = self.canvas
        cursor = x
        c.setFont(font, size)
        for is_emoji, value in self._rich_segments(line):
            if not is_emoji:
                c.drawString(cursor, baseline, value)
                cursor += pdfmetrics.stringWidth(value, font, size)
                continue
            glyph = self._emoji_image(value)
            if glyph is None:
                # A readable fallback is preferable to a missing-glyph square.
                c.drawString(cursor, baseline, "[emoji]")
                cursor += pdfmetrics.stringWidth("[emoji]", font, size)
                continue
            reader, ratio = glyph
            height = size + 1
            c.drawImage(reader, cursor, baseline - size * 0.2, height * ratio, height, mask="auto")
            cursor += height * ratio + 0.5

    def _draw_attachment_icon(self, x: float, y: float, kind: str) -> None:
        """Draw icons as vectors so they never depend on font glyph support."""
        c = self.canvas
        c.saveState()
        c.setStrokeColor(HexColor(self.theme.header))
        c.setFillColor(HexColor(self.theme.header))
        c.setLineWidth(1.4)
        if kind == "audio":
            for offset, height in ((-6, 5), (-3, 9), (0, 13), (3, 9), (6, 5)):
                c.line(x + offset, y - height / 2, x + offset, y + height / 2)
        elif kind == "video":
            c.circle(x, y, 8, fill=0, stroke=1)
            path = c.beginPath()
            path.moveTo(x - 2, y - 4)
            path.lineTo(x + 5, y)
            path.lineTo(x - 2, y + 4)
            path.close()
            c.drawPath(path, fill=1, stroke=0)
        else:
            c.roundRect(x - 6, y - 8, 12, 16, 1.5, fill=0, stroke=1)
            c.line(x - 3, y + 3, x + 3, y + 3)
            c.line(x - 3, y, x + 3, y)
            c.line(x - 3, y - 3, x + 2, y - 3)
        c.restoreState()
