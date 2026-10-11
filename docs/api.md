# Python API

```python
from whatsapp2pdf import LayoutConfig, PageSize, Theme, convert

result = convert(
    "WhatsApp Chat - Family.zip",
    "family.pdf",
    outgoing={"Jane Doe", "Jane"},   # names whose messages go on the right
    title="Family chat",             # default: taken from the file name
    config=LayoutConfig(page_size=PageSize.A5, font_size=10),
    day_first=True,                  # False for MM/DD exports
)
print(result.messages, result.output)
```

## `convert(source, output, *, outgoing=(), title=None, config=None, day_first=True, chat_member=None)`

Reads a `.zip` or `.txt` export and writes a PDF. Returns a `ConversionResult` with `output` (a `Path`) and `messages` (the number rendered).

## `LayoutConfig`

A frozen dataclass. Commonly used fields:

| Field | Default | Notes |
| --- | --- | --- |
| `page_size` | `PageSize.A4` | `PageSize.A4/A5/A6`, `"A5"`, or a `(width, height)` tuple in points. |
| `margin` | `36.0` | Points. |
| `font_size` | `9.5` | Message text size. |
| `max_bubble_width_ratio` | `0.75` | 0.3 to 0.95. |
| `media_max_height` | `220.0` | Maximum photo height, in points. |
| `image_scale` | `2.0` | Photo resolution relative to its printed size. |
| `font_path`, `bold_font_path` | bundled Noto Sans | Custom TrueType fonts. |
| `emoji_font_path` | system font | Color emoji font. |
| `show_cover`, `show_sender`, `show_page_numbers` | `True` | Toggle page elements. |
| `plain` | `False` | White page background. |
| `theme` | `Theme()` | Colors, see below. |

## `Theme`

All colors are hex strings. Change only the ones you need:

```python
Theme(page="#FFFFFF", outgoing="#DCF8C6", cover="#075E54")
```

`sender_tints` and `sender_names` are parallel tuples. Incoming senders take one slot each, in order of first appearance, and the slots cycle when there are more senders than colors.
