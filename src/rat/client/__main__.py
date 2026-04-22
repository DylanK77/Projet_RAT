from __future__ import annotations

import argparse
from pathlib import Path

from rat.client.app import ClientApp
from rat.core.tls import TLSPaths


def main() -> int:
    parser = argparse.ArgumentParser(description="Client TLS.")
    parser.add_argument("--host", required=True, help="Server host/IP")
    parser.add_argument("--port", type=int, default=8888, help="Server port (default: 8888)")
    parser.add_argument(
        "--server-name", default="localhost", help="TLS server name (default: localhost)"
    )
    parser.add_argument("--certs", default="certs", help="Certificates directory (default: certs)")
    args = parser.parse_args()

    certs = Path(args.certs)
    tls = TLSPaths(
        ca_cert=certs / "ca.pem",
        cert=certs / "client.pem",
        key=certs / "client-key.pem",
    )

    app = ClientApp(args.host, args.port, tls, server_name=args.server_name)
    try:
        app.run_forever()
    except KeyboardInterrupt:
        app.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())