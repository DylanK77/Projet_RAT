from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def _new_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _pem_key(key: rsa.RSAPrivateKey) -> bytes:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _pem_cert(cert: x509.Certificate) -> bytes:
    return cert.public_bytes(serialization.Encoding.PEM)


def generate(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.utcnow()
    valid_to = now + dt.timedelta(days=365)

    ca_key = _new_key()
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "RAT-CA")])
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(valid_to)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    def issue(cn: str) -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
        key = _new_key()
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(ca_name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(valid_to)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .sign(ca_key, hashes.SHA256())
        )
        return key, cert

    server_key, server_cert = issue("RAT-SERVER")
    client_key, client_cert = issue("RAT-CLIENT")

    (out / "ca.pem").write_bytes(_pem_cert(ca_cert))
    (out / "server.pem").write_bytes(_pem_cert(server_cert))
    (out / "server-key.pem").write_bytes(_pem_key(server_key))
    (out / "client.pem").write_bytes(_pem_cert(client_cert))
    (out / "client-key.pem").write_bytes(_pem_key(client_key))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate TLS certificates for development.")
    parser.add_argument("--out", default="certs", help="Output directory (default: certs)")
    args = parser.parse_args()
    generate(Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())