from __future__ import annotations

import socket
import ssl
import threading
import time
from dataclasses import dataclass

from rat.core.logging import LogSettings, setup_logging
from rat.core.rpc import RPCPeer
from rat.core.system_info import SystemInfo
from rat.core.tls import TLSPaths, create_server_context


@dataclass
class Session:
    session_id: str
    peer: RPCPeer
    info: SystemInfo | None
    addr: tuple[str, int]
    connected_at: float


class ServerApp:
    def __init__(self, host: str, port: int, tls_paths: TLSPaths) -> None:
        self.log = setup_logging(LogSettings(name="rat.server", filename="server.log"))
        self.host = host
        self.port = port
        self._ctx = create_server_context(tls_paths)
        self._sock: socket.socket | None = None
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()
        self._next_id = 1

    def start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.listen(50)
        self._sock = sock
        threading.Thread(target=self._accept_loop, name="accept", daemon=True).start()
        self.log.info("Listening on %s:%s (TLS)", self.host, self.port)

    def stop(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        with self._lock:
            for sess in list(self._sessions.values()):
                sess.peer.close()
            self._sessions.clear()

    def list_sessions(self) -> dict[str, Session]:
        with self._lock:
            return dict(self._sessions)

    def get_session(self, session_id: str) -> Session | None:
        with self._lock:
            return self._sessions.get(session_id)

    def remove_session(self, session_id: str) -> None:
        with self._lock:
            sess = self._sessions.pop(session_id, None)
        if sess is not None:
            sess.peer.close()

    def _accept_loop(self) -> None:
        assert self._sock is not None
        while True:
            try:
                raw_conn, addr = self._sock.accept()
            except OSError:
                break
            try:
                conn = self._ctx.wrap_socket(raw_conn, server_side=True)
            except ssl.SSLError as exc:
                self.log.warning("TLS handshake failed from %s: %s", addr, exc)
                try:
                    raw_conn.close()
                except OSError:
                    pass
                continue

            session_id = str(self._next_id)
            self._next_id += 1

            peer = RPCPeer(conn, name=f"session-{session_id}", logger=self.log)
            peer.start()

            sess = Session(
                session_id=session_id,
                peer=peer,
                info=None,
                addr=(addr[0], addr[1]),
                connected_at=time.time(),
            )
            with self._lock:
                self._sessions[session_id] = sess

            self.log.info("New connection: session_id=%s addr=%s", session_id, addr)

            try:
                evt = peer.next_event(timeout=2.0)
                if evt and evt.get("name") == "hello":
                    data = evt.get("data", {})
                    if isinstance(data, dict):
                        sess.info = SystemInfo(**data)  # type: ignore[arg-type]
                        self.log.info("Agent %s identified: %s", session_id, sess.info)
            except Exception:
                pass