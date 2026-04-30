from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DownloadItem:
    path: Path
    size: int


@dataclass
class UploadItem:
    path: Path
    size: int


class FileTransferState:
    def __init__(self) -> None:
        self._downloads: dict[str, DownloadItem] = {}
        self._uploads: dict[str, UploadItem] = {}

    def download_prepare(self, path: Path) -> tuple[str, int]:
        p = path.expanduser().resolve()
        size = p.stat().st_size
        token = str(uuid.uuid4())
        self._downloads[token] = DownloadItem(path=p, size=size)
        return token, size

    def download_read(self, token: str, offset: int, length: int) -> bytes:
        item = self._downloads[token]
        with item.path.open("rb") as f:
            f.seek(offset)
            return f.read(length)

    def download_finish(self, token: str) -> None:
        self._downloads.pop(token, None)

    def upload_prepare(self, path: Path, size: int) -> str:
        p = path.expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        token = str(uuid.uuid4())
        self._uploads[token] = UploadItem(path=p, size=size)
        # truncate/create
        p.write_bytes(b"")
        return token

    def upload_write(self, token: str, offset: int, chunk: bytes) -> None:
        item = self._uploads[token]
        with item.path.open("r+b") as f:
            f.seek(offset)
            f.write(chunk)

    def upload_finish(self, token: str) -> None:
        self._uploads.pop(token, None)

    def has_download(self, token: str) -> bool:
        return token in self._downloads

    def has_upload(self, token: str) -> bool:
        return token in self._uploads

    def get_download(self, token: str) -> DownloadItem | None:
        return self._downloads.get(token)
