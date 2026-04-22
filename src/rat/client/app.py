from __future__ import annotations

import socket
import ssl
import threading
import time
import uuid
from contextlib import suppress

from rat.client.state import ClientState
from rat.core.logging import LogSettings, setup_logging
from rat.core.rpc import RPCPeer
from rat.core.system_info import collect_system_info
from rat.core.tls import TLSPaths, create_client_context


class ClientApp:
    def __init__(self, host: str, port: int, tls_paths: TLSPaths, server_name: str) -> None:
        self.log = setup_logging(LogSettings(name="rat.client", filename="client.log"))
        self.host = host
        self.port = port
        self.server_name = server_name
        self.tls_paths = tls_paths
        self._ctx = create_client_context(tls_paths)
        self._state = ClientState()
        self._peer: RPCPeer | None = None
        self._stop = threading.Event()

    def run_forever(self) -> None:
        while not self._stop.is_set():
            try:
                self._connect_once()
            except Exception as exc:
                self.log.error("connect error: %s", exc)
            time.sleep(2.0)

    def stop(self) -> None:
        self._stop.set()
        if self._peer is not None:
            self._peer.close()

    def _connect_once(self) -> None:
        raw = socket.create_connection((self.host, self.port), timeout=10)
        try:
            conn: ssl.SSLSocket = self._ctx.wrap_socket(raw, server_hostname=self.server_name)
        except Exception:
            raw.close()
            raise

        session_id = str(uuid.uuid4())
        self._state.session_id = session_id
        self._state.connected = True

        peer = RPCPeer(conn, name="client", logger=self.log)
        self._peer = peer
        peer.start()

        peer.send_event("hello", collect_system_info().to_dict())
        self.log.info("Connected to %s:%s (session=%s, TLS)", self.host, self.port, session_id)

        while not peer.is_closed() and not self._stop.is_set():
            time.sleep(0.5)

        self._state.connected = False
        self._state.session_id = None
        self.log.info("Disconnected (session=%s).", session_id)

    def _close_peer(self) -> None:
        if self._peer is not None:
            with suppress(OSError):
                self._peer.close()
            self._peer = None