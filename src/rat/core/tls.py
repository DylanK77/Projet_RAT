from __future__ import annotations

import ssl
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TLSPaths:
    ca_cert: Path
    cert: Path
    key: Path


def create_server_context(paths: TLSPaths) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20")
    ctx.load_cert_chain(certfile=str(paths.cert), keyfile=str(paths.key))
    ctx.load_verify_locations(cafile=str(paths.ca_cert))
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = False
    return ctx


def create_client_context(paths: TLSPaths) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20")
    ctx.load_verify_locations(cafile=str(paths.ca_cert))
    ctx.load_cert_chain(certfile=str(paths.cert), keyfile=str(paths.key))
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx
