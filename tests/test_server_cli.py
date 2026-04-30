from __future__ import annotations

import base64

from rat.server.cli import _maybe_save_artifact


def test_maybe_save_artifact_accepts_nested_command_result(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    app = _FakeApp()

    _maybe_save_artifact(
        app,
        "1",
        {"ok": True, "data": {"filename": "screenshot.png", "bytes_b64": base64.b64encode(b"png").decode()}},
    )

    assert (tmp_path / "captures" / "agent-1" / "screenshot.png").read_bytes() == b"png"


class _FakeLog:
    def info(self, *args: object, **kwargs: object) -> None:
        pass

    def warning(self, *args: object, **kwargs: object) -> None:
        pass


class _FakeApp:
    log = _FakeLog()
