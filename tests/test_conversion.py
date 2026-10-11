import zipfile
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from whatsapp2pdf import LayoutConfig, PageSize, convert


def test_zip_conversion_with_image(tmp_path: Path):
    image_path = tmp_path / "photo.jpg"
    Image.new("RGB", (160, 90), "#25d366").save(image_path)
    archive = tmp_path / "export.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("_chat.txt", "15/08/26, 10:00 - Alice: Hello\n15/08/26, 10:01 - Me: photo.jpg (file attached)\n")
        output.write(image_path, "photo.jpg")
    destination = tmp_path / "chat.pdf"
    result = convert(archive, destination, outgoing="Me", config=LayoutConfig(font_size=10))
    reader = PdfReader(destination)
    assert result.messages == 2
    assert len(reader.pages) == 2  # cover + one chat page
    assert "Hello" in reader.pages[1].extract_text()


def test_page_size_selection(tmp_path: Path):
    chat = tmp_path / "chat.txt"
    chat.write_text("15/08/26, 10:00 - Alice: Hello\n", encoding="utf-8")
    expected = {
        PageSize.A4: (595.28, 841.89),
        PageSize.A5: (419.53, 595.28),
        PageSize.A6: (297.64, 419.53),
    }
    for size, dimensions in expected.items():
        destination = tmp_path / f"{size.value}.pdf"
        convert(chat, destination, config=LayoutConfig(page_size=size))
        box = PdfReader(destination).pages[0].mediabox
        assert round(float(box.width), 2) == dimensions[0]
        assert round(float(box.height), 2) == dimensions[1]


def test_day_separators_and_time_only_stamps(tmp_path: Path):
    chat = tmp_path / "chat.txt"
    chat.write_text(
        "14/03/26, 10:00 - Alice: Hello\n15/03/26, 11:30 - Me: Next day\n15/03/26, 11:31 - Alice: <Media omitted>\n",
        encoding="utf-8",
    )
    destination = tmp_path / "chat.pdf"
    convert(chat, destination, outgoing="Me")
    text = PdfReader(destination).pages[1].extract_text()
    assert "Saturday, 14 March 2026" in text
    assert "Sunday, 15 March 2026" in text
    assert "11:30" in text and "15/03/2026" not in text
    assert "Media not included in export" in text


def test_cover_page_totals_and_title(tmp_path: Path):
    chat = tmp_path / "WhatsApp Chat - Family.txt"
    chat.write_text(
        "14/03/26, 10:00 - Ana: Hi\n14/03/26, 10:01 - Luis: Hello\n"
        "14/03/26, 10:02 - Ana: IMG-1.jpg (file attached)\n16/03/26, 09:00 - Me: Morning\n",
        encoding="utf-8",
    )
    destination = tmp_path / "chat.pdf"
    convert(chat, destination, outgoing="Me")
    cover = PdfReader(destination).pages[0].extract_text()
    assert "Family" in cover
    assert "14 March 2026 to 16 March 2026" in cover
    assert "Me  (you)" in cover
    for number, label in (("4", "messages"), ("1", "photos"), ("3", "days")):
        assert f"{number}\n{label}" in cover


def test_no_cover_and_twelve_hour_clock(tmp_path: Path):
    chat = tmp_path / "chat.txt"
    chat.write_text("[3/14/26, 2:32:00 PM] Ana: Hi\n", encoding="utf-8")
    destination = tmp_path / "chat.pdf"
    convert(chat, destination, config=LayoutConfig(show_cover=False), day_first=False)
    reader = PdfReader(destination)
    assert len(reader.pages) == 1
    assert "2:32 pm" in reader.pages[0].extract_text()


def test_long_message_continues_on_next_page(tmp_path: Path):
    chat = tmp_path / "chat.txt"
    body = " ".join(f"word{i}" for i in range(3000))
    chat.write_text(f"14/03/26, 10:00 - Ana: {body}\n", encoding="utf-8")
    destination = tmp_path / "chat.pdf"
    convert(chat, destination, config=LayoutConfig(show_cover=False))
    reader = PdfReader(destination)
    assert len(reader.pages) > 1
    assert "continued" in reader.pages[0].extract_text()
    assert "word2999" in reader.pages[-1].extract_text()


def _zip_with_media(tmp_path: Path, name: str, data: bytes) -> Path:
    archive = tmp_path / "export.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
        output.writestr("_chat.txt", f"15/08/26, 10:00 - Alice: Look\n15/08/26, 10:01 - Alice: {name} (file attached)\n")
        output.writestr(name, data)
    return archive


def _png_bytes(width: int, height: int) -> bytes:
    import io

    buffer = io.BytesIO()
    Image.new("1", (width, height)).save(buffer, "PNG")
    return buffer.getvalue()


def test_decompression_bomb_image_becomes_attachment_card(tmp_path: Path, monkeypatch):
    # Lower Pillow's limit so a small image stands in for a real 200-megapixel bomb.
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100 * 100)
    for size, name in (((300, 300), "bomb.png"), ((150, 100), "warning.png")):  # error range, warning range
        archive = _zip_with_media(tmp_path, name, _png_bytes(*size))
        destination = tmp_path / f"{name}.pdf"
        result = convert(archive, destination, config=LayoutConfig(show_cover=False))
        assert result.messages == 2
        page = PdfReader(destination).pages[0]
        assert name in page.extract_text()  # shown as a card with its file name
        assert not page.images  # and never embedded


def test_disguised_eps_never_reaches_eps_decoder(tmp_path: Path, monkeypatch):
    from PIL import EpsImagePlugin

    opened = []
    monkeypatch.setattr(EpsImagePlugin.EpsImageFile, "_open", lambda self: opened.append(True))
    eps = b"%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 10 10\nshowpage\n%%EOF\n"
    archive = _zip_with_media(tmp_path, "photo.jpg", eps)
    destination = tmp_path / "chat.pdf"
    convert(archive, destination, config=LayoutConfig(show_cover=False))
    assert opened == []
    assert "photo.jpg" in PdfReader(destination).pages[0].extract_text()
