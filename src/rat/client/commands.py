from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Any

from rat.client.state import ClientState


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    data: dict[str, Any]


def _err(msg: str) -> CommandResult:
    return CommandResult(ok=False, data={"error": msg})


def cmd_help() -> CommandResult:
    return CommandResult(
        ok=True,
        data={
            "commands": [
                "help",
                "ipconfig",
            ]
        },
    )


def cmd_ipconfig() -> CommandResult:
    import platform
    import subprocess

    if platform.system().lower().startswith("win"):
        cmd = ["ipconfig", "/all"]
    else:
        cmd = ["sh", "-lc", "ip a || ifconfig -a"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=20, shell=False)  # noqa: S603
    out = ((p.stdout or "") + (p.stderr or "")).strip()
    return CommandResult(ok=(p.returncode == 0), data={"output": out, "exit_code": p.returncode})


def parse_and_run(state: ClientState, line: str) -> CommandResult:
    try:
        parts = shlex.split(line)
    except ValueError as exc:
        return _err(f"Parse error: {exc}")
    if not parts:
        return CommandResult(ok=True, data={})
    cmd, *args = parts[0].lower(), *parts[1:]

    if cmd == "help":
        return cmd_help()
    if cmd == "ipconfig":
        return cmd_ipconfig()

    return _err(f"Unknown command: {cmd} (try help)")