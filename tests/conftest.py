from __future__ import annotations

import socket
from collections.abc import Generator

import pytest


@pytest.fixture()
def socket_pair() -> Generator[tuple[socket.socket, socket.socket], None, None]:
    """Retourne une paire de sockets connectées, fermées automatiquement après le test."""
    a, b = socket.socketpair()
    try:
        yield a, b
    finally:
        a.close()
        b.close()