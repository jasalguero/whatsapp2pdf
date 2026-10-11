# Contributing

Thanks for helping! Bug reports, export formats that don't parse, and pull requests are all welcome.

## Setup

```bash
git clone https://github.com/jasalguero/whatsapp2pdf
cd whatsapp2pdf
python -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'
pytest
```

## Never share real chats

Please don't attach real WhatsApp exports to issues or commit them to the repo, even with the names changed. If a line doesn't parse, rewrite it with made-up names and text, and keep the timestamp and punctuation exactly as they were. Tests build their exports in `tmp_path`; follow that pattern.

## Pull requests

- Keep changes focused, and add a test for any parser or rendering fix.
- Visual changes: attach a screenshot of a page made from a synthetic chat.
- Add a line under "Unreleased" in `CHANGELOG.md`.
