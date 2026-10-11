from whatsapp2pdf.parser import parse_chat


def test_android_multiline_and_media():
    messages = list(parse_chat([
        "31/12/23, 23:58 - Alice: hello\n",
        "second line\n",
        "31/12/23, 23:59 - Bob: IMG-001.jpg (file attached)\n",
    ]))
    assert len(messages) == 2
    assert messages[0].text == "hello\nsecond line"
    assert messages[1].sender == "Bob"
    assert messages[1].media_name == "IMG-001.jpg"


def test_ios_format_and_system_message():
    messages = list(parse_chat([
        "[12/31/23, 11:59:01 PM] Alice: <attached: photo.jpg>\n",
        "[01/01/24, 12:00:00 AM] Messages are end-to-end encrypted.\n",
    ], day_first=False))
    assert messages[0].media_name == "photo.jpg"
    assert messages[0].timestamp.month == 12
    assert messages[1].is_system


def test_ios_localized_ampm_and_direction_marks():
    messages = list(parse_chat([
        "\u200e[04/08/2022, 9:32:43\u202fp.m.] Shaun: \u200e<attached: photo.jpg>\n",
        "[05/08/2022, 10:21:18\u202fa.m.] Veronica: Morning 👍\n",
    ]))
    assert messages[0].sender == "Shaun"
    assert messages[0].timestamp.hour == 21
    assert messages[0].media_name == "photo.jpg"
    assert messages[1].timestamp.hour == 10


def test_ios_encryption_notice_is_system_and_media_omitted():
    messages = list(parse_chat([
        "[14/03/26, 09:58:01] Ana: Messages and calls are end-to-end encrypted. Only people in this chat can read them.\n",
        "14/03/2026, 09:59 - Jose: <Media omitted>\n",
        "[14/03/26, 10:00:00] Ana: image omitted\n",
    ]))
    assert messages[0].is_system
    assert messages[0].text.startswith("Messages and calls")
    assert messages[1].media_omitted and messages[1].text == ""
    assert messages[2].media_omitted


def test_overlong_message_is_truncated(monkeypatch):
    import io

    from whatsapp2pdf import parser

    monkeypatch.setattr(parser, "MAX_MESSAGE_CHARS", 1000)
    monkeypatch.setattr(parser, "READ_CHUNK_CHARS", 64)
    huge = "x" * 50_000
    stream = io.StringIO(f"31/12/23, 23:58 - Alice: {huge}\nmore\n31/12/23, 23:59 - Bob: next\n")
    messages = list(parser.parse_text(stream))
    assert len(messages) == 2
    assert messages[0].text == "x" * 1000 + parser.TRUNCATED_MARK
    assert messages[1].sender == "Bob" and messages[1].text == "next"


def test_long_line_split_into_chunks_is_rejoined(monkeypatch):
    import io

    from whatsapp2pdf import parser

    monkeypatch.setattr(parser, "READ_CHUNK_CHARS", 40)  # headers always fit in one real chunk
    text = "a fairly long message that spans several read chunks"
    messages = list(parser.parse_text(io.StringIO(f"31/12/23, 23:58 - Alice: {text}\nsecond line\n")))
    assert messages[0].text == text + "\nsecond line"
