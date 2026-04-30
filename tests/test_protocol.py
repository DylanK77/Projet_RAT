from __future__ import annotations

import socket
import time

import pytest

from rat.core.protocol import Message, ProtocolError, recv_message, send_message
from rat.core.rpc import RPCPeer


def test_send_recv_roundtrip() -> None:
    a, b = socket.socketpair()
    try:
        send_message(a, Message(type="request", request_id="1", payload={"x": 1, "blob": b"abc"}))
        msg = recv_message(b, timeout=1.0)
        assert msg.type == "request"
        assert msg.request_id == "1"
        assert msg.payload["x"] == 1
        assert msg.payload["blob"] == b"abc"
    finally:
        a.close()
        b.close()


def test_invalid_frame_length_raises() -> None:
    a, b = socket.socketpair()
    try:
        b.sendall(b"\x00\x00\x00\x00")
        with pytest.raises(ProtocolError):
            recv_message(a, timeout=1.0)
    finally:
        a.close()
        b.close()


def test_rpc_peer_keeps_idle_connection_open_when_socket_has_connect_timeout() -> None:
    a, b = socket.socketpair()
    a.settimeout(0.05)
    peer = RPCPeer(a, name="test", logger=_NoopLogger())
    try:
        peer.start()
        time.sleep(0.15)

        assert not peer.is_closed()
    finally:
        peer.close()
        b.close()


class _NoopLogger:
    def info(self, *args: object, **kwargs: object) -> None:
        pass

    def warning(self, *args: object, **kwargs: object) -> None:
        pass

    def exception(self, *args: object, **kwargs: object) -> None:
        pass
