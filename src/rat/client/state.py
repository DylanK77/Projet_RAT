from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ClientState:
    connected: bool = False
    session_id: str | None = None