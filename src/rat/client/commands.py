from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Any

from rat.client.state import ClientState


@dataclass
class CommandResult:
    ok: bool
    data: dict[str, Any]


def cmd_help() -> CommandResult:
    return CommandResult(
        ok=True,
        data={
            "commands": [
                "help",
            ]
        },
    )


def parse_and_run(state: ClientState, line: str) -> CommandResult:
    parts = shlex.split(line)
    if not parts:
        return CommandResult(ok=True, data={})
    cmd = parts[0].lower()

    if cmd == "help":
        return cmd_help()

    return CommandResult(ok=False, data={"error": f"Unknown command: {cmd}"})