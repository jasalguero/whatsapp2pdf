# Security policy

whatsapp2pdf runs entirely on your machine. It never uploads chats or media, and it makes no network requests.

## Supported versions

Security fixes go into the latest release only.

## Reporting a vulnerability

Please do not open a public issue. Instead, use GitHub's private vulnerability reporting: open the repository's **Security** tab and choose **Report a vulnerability**. Include a minimal export (synthetic data, please) that reproduces the problem.

You should get a response within a week.

## Threat model

Exports may come from other people, so the converter treats every ZIP, chat file and media file as untrusted:

- Nothing is extracted to disk. Media is read from inside the ZIP by its bare file name, so archive paths such as `../../x` cannot escape.
- Images are decoded by Pillow, restricted to common photo formats, and skipped when they exceed Pillow's decompression-bomb limit.
- A single message is capped in size, so a crafted one-line chat cannot exhaust memory.
- Text is never interpreted as markup or code.

Bugs that let a crafted export write outside the output path, run code, or exhaust memory or disk are in scope.
