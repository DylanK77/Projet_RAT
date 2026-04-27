from __future__ import annotations

import socket
import struct

import pytest

from rat.core.protocol import Message, ProtocolError, recv_message, send_message

_LEN_STRUCT = struct.Struct("!I")

# Message dataclass

def test_message_to_dict_roundtrip() -> None:
    msg = Message(type="event", request_id="abc", payload={"k": 42})
    d = msg.to_dict()
    assert d == {"type": "event", "request_id": "abc", "payload": {"k": 42}}
    restored = Message.from_dict(d)
    assert restored == msg


def test_message_from_dict_invalid_container() -> None:
    with pytest.raises(ProtocolError):
        Message.from_dict("not a dict")  # type: ignore[arg-type]


def test_message_from_dict_missing_fields() -> None:
    with pytest.raises(ProtocolError):
        Message.from_dict({"type": "request"})  # request_id manquant


def test_message_from_dict_wrong_types() -> None:
    with pytest.raises(ProtocolError):
        Message.from_dict({"type": 123, "request_id": "1", "payload": {}})


def test_message_frozen() -> None:
    msg = Message(type="request", request_id="1", payload={})
    with pytest.raises(Exception):
        msg.type = "event"  # type: ignore[misc]

# send_message / recv_message

def test_send_recv_roundtrip(socket_pair: tuple[socket.socket, socket.socket]) -> None:
    a, b = socket_pair
    send_message(a, Message(type="request", request_id="1", payload={"x": 1, "blob": b"abc"}))
    msg = recv_message(b, timeout=1.0)
    assert msg.type == "request"
    assert msg.request_id == "1"
    assert msg.payload["x"] == 1
    assert msg.payload["blob"] == b"abc"


def test_send_recv_empty_payload(socket_pair: tuple[socket.socket, socket.socket]) -> None:
    a, b = socket_pair
    send_message(a, Message(type="event", request_id="x", payload={}))
    msg = recv_message(b, timeout=1.0)
    assert msg.payload == {}


def test_send_recv_nested_payload(socket_pair: tuple[socket.socket, socket.socket]) -> None:
    a, b = socket_pair
    payload = {"nested": {"list": [1, 2, 3], "bytes": b"\x00\xff"}}
    send_message(a, Message(type="response", request_id="r1", payload=payload))
    msg = recv_message(b, timeout=1.0)
    assert msg.payload["nested"]["list"] == [1, 2, 3]
    assert msg.payload["nested"]["bytes"] == b"\x00\xff"


def test_recv_frame_length_zero_raises(socket_pair: tuple[socket.socket, socket.socket]) -> None:
    a, b = socket_pair
    b.sendall(b"\x00\x00\x00\x00")
    with pytest.raises(ProtocolError):
        recv_message(a, timeout=1.0)


def test_recv_frame_length_too_large_raises(
    socket_pair: tuple[socket.socket, socket.socket],
) -> None:
    a, b = socket_pair
    b.sendall(_LEN_STRUCT.pack(100_000_001))  # > MAX_MESSAGE_SIZE
    with pytest.raises(ProtocolError):
        recv_message(a, timeout=1.0)


def test_recv_connection_closed_mid_frame_raises(
    socket_pair: tuple[socket.socket, socket.socket],
) -> None:
    a, b = socket_pair
    b.sendall(b"\x00\x00\x00")  # header incomplet — 3 octets sur 4
    b.close()
    with pytest.raises(ProtocolError):
        recv_message(a, timeout=1.0)


def test_timeout_restored_after_recv(socket_pair: tuple[socket.socket, socket.socket]) -> None:
    a, b = socket_pair
    a.settimeout(5.0)
    send_message(b, Message(type="event", request_id="t", payload={}))
    recv_message(a, timeout=1.0)
    assert a.gettimeout() == pytest.approx(5.0)