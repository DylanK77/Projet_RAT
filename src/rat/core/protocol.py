from __future__ import annotations

import socket
import struct
from dataclasses import dataclass
from typing import Any

import msgpack


class ProtocolError(RuntimeError):
    pass


_LEN_STRUCT = struct.Struct("!I")  # 4-byte unsigned big-endian length


@dataclass(frozen=True)
class Message:
    type: str
    request_id: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "request_id": self.request_id, "payload": self.payload}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Message:
        if not isinstance(data, dict):
            raise ProtocolError("Invalid message container")
        msg_type = data.get("type")
        req_id = data.get("request_id")
        payload = data.get("payload", {})
        if (
            not isinstance(msg_type, str)
            or not isinstance(req_id, str)
            or not isinstance(payload, dict)
        ):
            raise ProtocolError("Invalid message fields")
        return Message(type=msg_type, request_id=req_id, payload=payload)


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    chunks: list[bytes] = []
    remaining = n
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ProtocolError("Connection closed while receiving")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def send_message(sock: socket.socket, message: Message) -> None:
    packed = msgpack.packb(message.to_dict(), use_bin_type=True)
    if len(packed) > 50_000_000:
        raise ProtocolError("Message too large")
    sock.sendall(_LEN_STRUCT.pack(len(packed)) + packed)


def recv_message(sock: socket.socket, *, timeout: float | None = None) -> Message:
    old_timeout = sock.gettimeout()
    try:
        if timeout is not None:
            sock.settimeout(timeout)
        header = _recv_exact(sock, _LEN_STRUCT.size)
        (length,) = _LEN_STRUCT.unpack(header)
        if length == 0 or length > 50_000_000:
            raise ProtocolError(f"Invalid frame length: {length}")
        payload = _recv_exact(sock, length)
        data = msgpack.unpackb(payload, raw=False)
        if not isinstance(data, dict):
            raise ProtocolError("Invalid message payload")
        return Message.from_dict(data)
    finally:
        sock.settimeout(old_timeout)
