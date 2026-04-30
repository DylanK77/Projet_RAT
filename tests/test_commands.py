from __future__ import annotations

from pathlib import Path

from rat.client import commands


def test_record_audio_uses_sounddevice_wait_without_timeout(monkeypatch) -> None:
    def fake_rec(frames, *, samplerate, channels, dtype):
        return [[0.0]] * frames

    def fake_wait() -> None:
        return None

    def fake_write(path: Path, audio, sample_rate: int, *, format: str) -> None:
        path.write_bytes(b"wav")

    monkeypatch.setattr(commands.sd, "rec", fake_rec)
    monkeypatch.setattr(commands.sd, "wait", fake_wait)
    monkeypatch.setattr(commands.sf, "write", fake_write)

    result = commands.cmd_record_audio(0.1)

    assert result.ok
    assert result.data["filename"] == "audio.wav"
    assert result.data["bytes_b64"]
