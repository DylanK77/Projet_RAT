from __future__ import annotations

import uuid
from pathlib import Path


class FileTransferState:
    def __init__(self) -> None:
        self._downloads: dict[str, Path] = {}
        self._uploads: dict[str, Path] = {}

    def download_prepare(self, path: Path) -> tuple[str, int]:
        p = path.expanduser().resolve()
        size = p.stat().st_size
        token = str(uuid.uuid4())
        self._downloads[token] = p
        return token, size

    def download_read(self, token: str, offset: int, length: int) -> bytes:
        p = self._downloads[token]
        with p.open("rb") as f:
            f.seek(offset)
            return f.read(length)

    def download_finish(self, token: str) -> None:
        self._downloads.pop(token, None)

    def upload_prepare(self, path: Path, size: int) -> str:
        p = path.expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        token = str(uuid.uuid4())
        self._uploads[token] = p
        p.write_bytes(b"")
        return token

    def upload_write(self, token: str, offset: int, chunk: bytes) -> None:
        p = self._uploads[token]
        with p.open("r+b") as f:
            f.seek(offset)
            f.write(chunk)

    def upload_finish(self, token: str) -> None:
        self._uploads.pop(token, None)