# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-10

### Added
- First public release.
- Streaming conversion of WhatsApp `.zip` and `.txt` exports (Android and iOS) to bubble-style PDFs.
- Cover page, day separators, per-sender bubble colors, inline photos, attachment cards and large emoji.
- A4, A5 and A6 page sizes, a plain (white) mode, and an option to skip the cover.
- Bundled Noto Sans fonts.

### Security
- Images that exceed Pillow's decompression-bomb limit are shown as attachment cards instead of being loaded.
- Images open only in common photo formats (JPEG, PNG, WebP, GIF, BMP, TIFF), whatever the file extension says.
- Very long single messages are capped and marked as truncated.
