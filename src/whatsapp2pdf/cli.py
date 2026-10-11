from __future__ import annotations

import argparse
from pathlib import Path

from .config import LayoutConfig, PageSize
from .converter import convert


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert a WhatsApp export to a bubble-style PDF")
    parser.add_argument("source", help="WhatsApp .zip export or chat .txt file")
    parser.add_argument("output", help="Destination PDF")
    parser.add_argument("--me", action="append", default=[], help="Your sender name (repeat for aliases)")
    parser.add_argument("--title", help="Chat title (default: taken from the export's file name)")
    parser.add_argument("--font-size", type=float, default=9.5)
    parser.add_argument("--margin", type=float, default=36.0)
    parser.add_argument("--bubble-width", type=float, default=0.75, metavar="RATIO")
    parser.add_argument(
        "--page-size", choices=[size.value for size in PageSize], default=PageSize.A4.value,
        help="PDF page layout (default: A4)",
    )
    parser.add_argument("--font", type=Path, help="Path to a Unicode .ttf font")
    parser.add_argument("--bold-font", type=Path, help="Path to its bold .ttf font")
    parser.add_argument("--emoji-font", type=Path, help="Path to a color emoji font (default: the system's)")
    parser.add_argument("--plain", action="store_true", help="White page background, for cheaper printing")
    parser.add_argument("--no-cover", action="store_true", help="Skip the cover page")
    parser.add_argument("--month-first", action="store_true", help="Interpret ambiguous dates as MM/DD")
    parser.add_argument("--chat-member", help="Specific .txt member inside the ZIP")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = LayoutConfig(
        font_size=args.font_size,
        margin=args.margin,
        max_bubble_width_ratio=args.bubble_width,
        page_size=args.page_size,
        font_path=args.font,
        bold_font_path=args.bold_font,
        emoji_font_path=args.emoji_font,
        plain=args.plain,
        show_cover=not args.no_cover,
    )
    result = convert(
        args.source, args.output, outgoing=set(args.me), title=args.title,
        config=config, day_first=not args.month_first, chat_member=args.chat_member,
    )
    print(f"Wrote {result.messages} messages to {result.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
