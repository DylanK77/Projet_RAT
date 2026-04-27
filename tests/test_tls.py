from __future__ import annotations

import ssl
import tempfile
from pathlib import Path

import pytest

from rat.core.tls import TLSPaths, create_client_context, create_server_context
from rat.tools.gen_certs import generate


@pytest.fixture(scope="module")
def certs_dir() -> Path:
    """Génère des certificats de test dans un répertoire temporaire."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        generate(d)
        yield d


@pytest.fixture(scope="module")
def tls_paths(certs_dir: Path) -> TLSPaths:
    return TLSPaths(
        ca_cert=certs_dir / "ca.pem",
        cert=certs_dir / "server.pem",
        key=certs_dir / "server-key.pem",
    )


@pytest.fixture(scope="module")
def client_paths(certs_dir: Path) -> TLSPaths:
    return TLSPaths(
        ca_cert=certs_dir / "ca.pem",
        cert=certs_dir / "client.pem",
        key=certs_dir / "client-key.pem",
    )


def test_server_context_is_ssl_context(tls_paths: TLSPaths) -> None:
    ctx = create_server_context(tls_paths)
    assert isinstance(ctx, ssl.SSLContext)


def test_server_context_verify_mode(tls_paths: TLSPaths) -> None:
    ctx = create_server_context(tls_paths)
    assert ctx.verify_mode == ssl.CERT_REQUIRED


def test_server_context_minimum_version(tls_paths: TLSPaths) -> None:
    ctx = create_server_context(tls_paths)
    assert ctx.minimum_version >= ssl.TLSVersion.TLSv1_2


def test_client_context_is_ssl_context(client_paths: TLSPaths) -> None:
    ctx = create_client_context(client_paths)
    assert isinstance(ctx, ssl.SSLContext)


def test_client_context_verify_mode(client_paths: TLSPaths) -> None:
    ctx = create_client_context(client_paths)
    assert ctx.verify_mode == ssl.CERT_REQUIRED


def test_client_context_check_hostname(client_paths: TLSPaths) -> None:
    ctx = create_client_context(client_paths)
    assert ctx.check_hostname is True


def test_tls_paths_frozen(tls_paths: TLSPaths) -> None:
    with pytest.raises(Exception):
        tls_paths.ca_cert = Path("/tmp/tampered")  # type: ignore[misc]


def test_missing_cert_raises(certs_dir: Path) -> None:
    bad = TLSPaths(
        ca_cert=certs_dir / "ca.pem",
        cert=certs_dir / "nonexistent.pem",
        key=certs_dir / "server-key.pem",
    )
    with pytest.raises(Exception):
        create_server_context(bad)