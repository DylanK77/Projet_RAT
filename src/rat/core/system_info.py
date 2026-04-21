from __future__ import annotations

import getpass
import platform
import socket
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SystemInfo:
    hostname: str
    username: str
    os: str
    os_version: str
    arch: str
    python: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_system_info() -> SystemInfo:
    return SystemInfo(
        hostname=socket.gethostname(),
        username=getpass.getuser(),
        os=platform.system(),
        os_version=platform.version(),
        arch=platform.machine(),
        python=platform.python_version(),
    )