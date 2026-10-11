"""ZIP and filesystem export sources for whatsapp2pdf."""

from __future__ import annotations

import io
import mimetypes
import zipfile
from contextlib import AbstractContextManager
from pathlib import Path, PurePosixPath
from typing import BinaryIO


class ExportSource(AbstractContextManager["ExportSource"]):
    """A chat stream plus random, on-demand access to exported media."""

    def __init__(self, path: str | Path, *, chat_member: str | None = None) -> None:
        self.path = Path(path)
        self.chat_member = chat_member
        self._zip: zipfile.ZipFile | None = None
        self._chat_binary: BinaryIO | None = None
        self._names: dict[str, str] = {}

    def __enter__(self) -> "ExportSource":
        if self.path.suffix.lower() == ".zip":
            self._zip = zipfile.ZipFile(self.path)
            members = [info.filename for info in self._zip.infolist() if not info.is_dir()]
            self._names = {PurePosixPath(name).name.casefold(): name for name in members}
            chosen = self.chat_member
            if chosen is None:
                texts = [name for name in members if name.lower().endswith(".txt")]
                if not texts:
                    raise ValueError("ZIP contains no .txt chat export")
                chosen = max(texts, key=lambda name: self._zip.getinfo(name).file_size)
            self._chat_binary = self._zip.open(chosen)
        else:
            self._chat_binary = self.path.open("rb")
        return self

    @property
    def chat(self) -> io.TextIOWrapper:
        if self._chat_binary is None:
            raise RuntimeError("ExportSource must be used as a context manager")
        return io.TextIOWrapper(self._chat_binary, encoding="utf-8-sig", errors="replace")

    def open_media(self, name: str) -> BinaryIO | None:
        if self._zip is None:
            candidate = self.path.parent / PurePosixPath(name).name
            return candidate.open("rb") if candidate.is_file() else None
        member = self._names.get(PurePosixPath(name).name.casefold())
        return self._zip.open(member) if member else None

    @staticmethod
    def media_kind(name: str) -> str:
        mime, _ = mimetypes.guess_type(name)
        return mime.split("/", 1)[0] if mime else "document"

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._chat_binary is not None:
            self._chat_binary.close()
        if self._zip is not None:
            self._zip.close()
