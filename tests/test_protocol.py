from __future__ import annotations

import socket

import pytest

from rat.core.protocol import Message, ProtocolError, recv_message, send_message


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