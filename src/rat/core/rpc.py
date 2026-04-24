from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from queue import Queue
from typing import Any

from rat.core.protocol import Message, ProtocolError, recv_message, send_message


class RPCClosed(RuntimeError):
    pass


@dataclass(frozen=True)
class RPCRequest:
    request_id: str
    command: str
    args: dict[str, Any]


Handler = Callable[[RPCRequest], dict[str, Any]]


class RPCPeer:
    """
    Bidirectional request/response messaging over an already-secured socket.

    - Requests:  type="request",  payload={"command": str, "args": dict}
    - Responses: type="response", payload={"ok": bool, "result": dict, "error": str|None}
    - Events:    type="event",    payload={"name": str, "data": dict}
    """

    def __init__(self, sock, *, name: str, logger) -> None:
        self._sock = sock
        self._name = name
        self._log = logger
        self._handlers: dict[str, Handler] = {}
        self._responses: dict[str, Queue[Message]] = {}
        self._events: Queue[Message] = Queue()
        self._closed = threading.Event()
        self._rx_thread = threading.Thread(
            target=self._rx_loop, name=f"{name}-rx", daemon=True
        )

    def start(self) -> None:
        self._rx_thread.start()

    def close(self) -> None:
        self._closed.set()
        with suppress(OSError):
            self._sock.close()

    def is_closed(self) -> bool:
        return self._closed.is_set()

    def on(self, command: str, handler: Handler) -> None:
        self._handlers[command] = handler

    def send_event(self, name: str, data: dict[str, Any]) -> None:
        if self.is_closed():
            raise RPCClosed()
        send_message(
            self._sock,
            Message(
                type="event",
                request_id=str(uuid.uuid4()),
                payload={"name": name, "data": data},
            ),
        )

    def request(
        self, command: str, args: dict[str, Any], *, timeout: float = 30.0
    ) -> dict[str, Any]:
        if self.is_closed():
            raise RPCClosed()
        request_id = str(uuid.uuid4())
        q: Queue[Message] = Queue(maxsize=1)
        self._responses[request_id] = q
        try:
            send_message(
                self._sock,
                Message(
                    type="request",
                    request_id=request_id,
                    payload={"command": command, "args": args},
                ),
            )
            try:
                resp = q.get(timeout=timeout)
            except Exception as exc:
                raise TimeoutError(f"Timeout waiting for response to {command}") from exc
            payload = resp.payload
            if not payload.get("ok", False):
                raise RuntimeError(payload.get("error") or "Unknown error")
            result = payload.get("result", {})
            if not isinstance(result, dict):
                raise ProtocolError("Invalid result")
            return result
        finally:
            self._responses.pop(request_id, None)

    def next_event(self, *, timeout: float | None = None) -> dict[str, Any] | None:
        try:
            msg = self._events.get(timeout=timeout)
        except Exception:
            return None
        return msg.payload

    def _send_response(
        self, request_id: str, *, ok: bool, result: dict[str, Any], error: str | None
    ) -> None:
        try:
            send_message(
                self._sock,
                Message(
                    type="response",
                    request_id=request_id,
                    payload={"ok": ok, "result": result, "error": error},
                ),
            )
        except OSError as exc:
            self._log.warning("send_response failed: %s", exc)

    def _dispatch_request(self, msg: Message) -> None:
        payload = msg.payload
        cmd = payload.get("command")
        args = payload.get("args", {})
        if not isinstance(cmd, str) or not isinstance(args, dict):
            self._send_response(
                msg.request_id, ok=False, result={}, error="Invalid request format"
            )
            return
        handler = self._handlers.get(cmd)
        if handler is None:
            self._send_response(
                msg.request_id, ok=False, result={}, error=f"Unknown command: {cmd}"
            )
            return
        try:
            started = time.time()
            res = handler(RPCRequest(request_id=msg.request_id, command=cmd, args=args))
            took_ms = int((time.time() - started) * 1000)
            self._send_response(
                msg.request_id,
                ok=True,
                result={"data": res, "took_ms": took_ms},
                error=None,
            )
        except Exception as exc:
            self._log.exception("handler error for %s", cmd)
            self._send_response(
                msg.request_id,
                ok=False,
                result={},
                error=f"{type(exc).__name__}: {exc}",
            )

    def _rx_loop(self) -> None:
        while not self._closed.is_set():
            try:
                msg = recv_message(self._sock)
            except (OSError, ProtocolError) as exc:
                self._log.info("connection closed: %s", exc)
                self._closed.set()
                break

            if msg.type == "response":
                q = self._responses.get(msg.request_id)
                if q is not None:
                    with suppress(Exception):
                        q.put_nowait(msg)
                continue

            if msg.type == "event":
                self._events.put(msg)
                continue

            if msg.type == "request":
                self._dispatch_request(msg)
                continue

            self._log.warning("unknown message type: %s", msg.type)