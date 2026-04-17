from __future__ import annotations

import argparse
import datetime as dt
from ipaddress import ip_address
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID, ObjectIdentifier


def _write_pem(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _new_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=3072)


def _name(common_name: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _pem_key(key: rsa.RSAPrivateKey) -> bytes:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _pem_cert(cert: x509.Certificate) -> bytes:
    return cert.public_bytes(serialization.Encoding.PEM)


def generate(certs_dir: Path, *, days: int = 365) -> None:
    now = _now()
    valid_to = now + dt.timedelta(days=days)

    ca_key = _new_key()
    ca_subject = _name("RAT-CA")
    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(ca_subject)
        .issuer_name(ca_subject)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=1))
        .not_valid_after(valid_to)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )

    def issue_leaf(
        common_name: str, *, eku: ObjectIdentifier
    ) -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
        key = _new_key()
        subject = _name(common_name)
        san = x509.SubjectAlternativeName(
            [
                x509.DNSName("localhost"),
                x509.IPAddress(ip_address("127.0.0.1")),
            ]
        )
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(minutes=1))
            .not_valid_after(valid_to)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(san, critical=False)
            .add_extension(x509.ExtendedKeyUsage([eku]), critical=False)
            .sign(ca_key, hashes.SHA256())
        )
        return key, cert

    server_key, server_cert = issue_leaf("RAT-SERVER", eku=ExtendedKeyUsageOID.SERVER_AUTH)
    client_key, client_cert = issue_leaf("RAT-CLIENT", eku=ExtendedKeyUsageOID.CLIENT_AUTH)

    _write_pem(certs_dir / "ca.pem", _pem_cert(ca_cert))
    _write_pem(certs_dir / "server.pem", _pem_cert(server_cert))
    _write_pem(certs_dir / "server-key.pem", _pem_key(server_key))
    _write_pem(certs_dir / "client.pem", _pem_cert(client_cert))
    _write_pem(certs_dir / "client-key.pem", _pem_key(client_key))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate CA + server/client TLS certificates for the RAT project."
    )
    parser.add_argument("--out", default="certs", help="Output directory (default: certs)")
    parser.add_argument("--days", type=int, default=365, help="Validity in days (default: 365)")
    args = parser.parse_args()

    generate(Path(args.out), days=args.days)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())