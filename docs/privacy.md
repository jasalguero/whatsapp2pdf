# Privacy & security

## Your chats stay on your computer

whatsapp2pdf is a local program. It never uploads anything, needs no account, and makes no network requests. The PDF it writes contains your conversation, so treat it as you would the export itself.

## Untrusted exports

Exports can come from other people, so the converter treats every file as untrusted:

- **Nothing is extracted to disk.** Media is read directly from the ZIP and looked up by bare file name, so paths like `../../file` inside an archive cannot write or read outside it.
- **Images are decoded by Pillow, limited to common photo formats**, and very large "decompression bomb" images are skipped and shown as attachment cards.
- **Text is drawn as plain text** and is never interpreted as markup or code.

Found a problem? Please report it privately. See [`SECURITY.md`](https://github.com/jasalguero/whatsapp2pdf/blob/main/SECURITY.md).

## Fonts and emoji

- Text uses **Noto Sans**, which ships with the package under the SIL Open Font License 1.1.
- **Emoji are not bundled.** They're drawn from a color emoji font already on your system (Apple Color Emoji, Noto Color Emoji or Segoe UI Emoji), or from `--emoji-font`. The emoji images embedded in your PDF stay subject to that font's license. That's fine for personal archives; if you plan to publish PDFs, [Noto Color Emoji](https://github.com/googlefonts/noto-emoji) (OFL) is the safest choice.
