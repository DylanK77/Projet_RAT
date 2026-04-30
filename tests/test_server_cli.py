from __future__ import annotations

import base64

from rat.server.cli import (
    AGENT_COMMAND_LINES,
    SERVER_COMMANDS,
    _command_suffix,
    _handle_agent_command,
    _maybe_save_artifact,
    _save_stream_snapshot_frame,
)


def test_command_suffix_supports_server_and_agent_commands() -> None:
    assert _command_suffix("se", SERVER_COMMANDS) == "ssions"
    assert _command_suffix("webcam_stream sta", AGENT_COMMAND_LINES) == "rt "
    assert _command_suffix("record_", AGENT_COMMAND_LINES) == "audio "


def test_maybe_save_artifact_accepts_nested_command_result(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    app = _FakeApp()

    saved = _maybe_save_artifact(
        app,
        "1",
        {
            "ok": True,
            "data": {
                "filename": "screenshot.png",
                "bytes_b64": base64.b64encode(b"png").decode(),
            },
        },
    )

    assert saved is not None
    assert saved.resolve() == tmp_path / "captures" / "agent-1" / "screenshot.png"
    assert (tmp_path / "captures" / "agent-1" / "screenshot.png").read_bytes() == b"png"
    assert app.log.messages == [f"Saved artifact to {saved}"]


def test_agent_artifact_command_does_not_log_base64_result(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    app = _FakeApp(
        session=_FakeSession(
            "1",
            _FakePeer(
                {
                    "data": {
                        "ok": True,
                        "data": {
                            "filename": "audio.wav",
                            "bytes_b64": base64.b64encode(b"wav").decode(),
                        },
                    }
                }
            ),
        )
    )
    state = _FakeState(active_session_id="1")

    _handle_agent_command(app, state, "record_audio 1")

    assert (tmp_path / "captures" / "agent-1" / "audio.wav").read_bytes() == b"wav"
    assert all("bytes_b64" not in message for message in app.log.messages)


def test_webcam_stream_saves_live_frame_events(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    app = _FakeApp(
        session=_FakeSession(
            "1",
            _FakePeer(
                {"data": {"token": "stream-token"}},
                {"data": {"stopped": True}},
                events=[
                    {
                        "name": "webcam_frame",
                        "data": {"token": "stream-token", "jpeg": b"jpg"},
                    }
                ],
            ),
        )
    )

    _handle_agent_command(app, _FakeState(active_session_id="1"), "webcam_stream start 1")

    frames = list((tmp_path / "captures" / "agent-1" / "webcam_stream").glob("frame-*.jpg"))
    assert frames
    assert frames[0].read_bytes() == b"jpg"


def test_webcam_stream_snapshot_frame_decoder_still_handles_nested_results(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "captures" / "agent-1" / "webcam_stream"
    out_dir.mkdir(parents=True)

    saved = _save_stream_snapshot_frame(
        out_dir,
        0,
        {
            "data": {
                "ok": True,
                "data": {
                    "filename": "webcam.jpg",
                    "bytes_b64": base64.b64encode(b"jpg").decode(),
                },
            }
        },
    )

    assert saved == 1
    assert (out_dir / "frame-00000.jpg").read_bytes() == b"jpg"


class _FakeLog:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, *args: object, **kwargs: object) -> None:
        self.messages.append(str(args[0]) % args[1:] if args else "")

    def warning(self, *args: object, **kwargs: object) -> None:
        self.messages.append(str(args[0]) % args[1:] if args else "")

    def error(self, *args: object, **kwargs: object) -> None:
        self.messages.append(str(args[0]) % args[1:] if args else "")


class _FakeApp:
    def __init__(self, session: _FakeSession | None = None) -> None:
        self.log = _FakeLog()
        self.session = session

    def get_session(self, session_id: str):
        if self.session is not None and self.session.session_id == session_id:
            return self.session
        return None


class _FakeState:
    def __init__(self, active_session_id: str) -> None:
        self.active_session_id = active_session_id


class _FakeSession:
    def __init__(self, session_id: str, peer: _FakePeer) -> None:
        self.session_id = session_id
        self.peer = peer


class _FakePeer:
    def __init__(self, *responses: object, events: list[object] | None = None) -> None:
        self.responses = list(responses)
        self.events = list(events or [])

    def request(self, *args: object, **kwargs: object):
        return self.responses.pop(0)

    def next_event(self, *args: object, **kwargs: object):
        if self.events:
            return self.events.pop(0)
        return None
