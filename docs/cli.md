# Command line

```bash
whatsapp2pdf SOURCE OUTPUT [options]
```

`SOURCE` is a WhatsApp `.zip` export or a chat `.txt`. `OUTPUT` is the PDF to write; missing folders are created.

## Examples

```bash
# Your own messages on the right (repeat --me for each name you appear under)
whatsapp2pdf export.zip chat.pdf --me "Jane Doe" --me "Jane"

# A5 book-style pages with a custom title
whatsapp2pdf export.zip chat-a5.pdf --me "Jane Doe" --page-size A5 --title "Family chat"

# Plain white pages, no cover
whatsapp2pdf export.zip print.pdf --plain --no-cover

# US-style export where dates are MM/DD
whatsapp2pdf export.zip chat.pdf --month-first
```

## Options

| Option | Default | What it does |
| --- | --- | --- |
| `--me NAME` | none | Your sender name. Its messages go on the right. Repeat for aliases. |
| `--title TEXT` | from the file name | Title on the cover and in the page header. "WhatsApp Chat - Family.zip" becomes "Family". |
| `--page-size A4\|A5\|A6` | `A4` | Page format. |
| `--font-size PT` | `9.5` | Message text size. |
| `--margin PT` | `36` | Page margin. |
| `--bubble-width RATIO` | `0.75` | Maximum bubble width as a share of the text area (0.3 to 0.95). |
| `--plain` | off | White page background instead of beige. |
| `--no-cover` | off | Skip the cover page. |
| `--month-first` | off | Read ambiguous dates such as `03/04/26` as month/day. |
| `--font PATH` / `--bold-font PATH` | bundled Noto Sans | TrueType fonts for other scripts (e.g. Noto Sans Arabic, CJK). |
| `--emoji-font PATH` | system font | A color emoji font, e.g. `NotoColorEmoji.ttf`. |
| `--chat-member NAME` | largest `.txt` | Which `.txt` inside the ZIP is the chat. |
