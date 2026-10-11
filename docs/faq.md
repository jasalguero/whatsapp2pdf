# FAQ

**My messages are on the left.**
Pass the exact name WhatsApp shows for you with `--me`. Repeat it for each name you appear under, for example your name on another phone.

**Dates are wrong, e.g. 3 April instead of 4 March.**
Your export uses month/day order. Add `--month-first`.

**Emoji show as empty boxes or plain text.**
No color emoji font was found. Install Noto Color Emoji (`fonts-noto-color-emoji` on Debian/Ubuntu) or pass `--emoji-font /path/to/NotoColorEmoji.ttf`.

**Arabic, Hebrew, Chinese, Japanese or other scripts look wrong.**
The bundled Noto Sans covers Latin, Greek and Cyrillic. Pass a font that covers your script with `--font` and `--bold-font`, e.g. Noto Sans Arabic or Noto Sans CJK.

**Photos say "Media not included in export".**
The chat was exported **without media**, or WhatsApp left those files out. Export again with media.

**The ZIP is huge. Will it work?**
Yes. Messages are streamed and photos are read from the ZIP one at a time, so memory use stays low. Runtime and PDF size grow with the number of photos.

**A line of my chat isn't parsed correctly.**
Please [open an issue](https://github.com/jasalguero/whatsapp2pdf/issues) with a few lines rewritten using made-up names and text, keeping the timestamps and punctuation exactly as in your export. Please don't attach real chats.
