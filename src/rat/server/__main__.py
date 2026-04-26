from __future__ import annotations

import argparse
from pathlib import Path

from rat.core.tls import TLSPaths
from rat.server.app import ServerApp
from rat.server.cli import run_cli


def main() -> int:
    parser = argparse.ArgumentParser(description="RAT server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8888)
    parser.add_argument("--certs", default="certs")
    args = parser.parse_args()

    certs = Path(args.certs)
    tls = TLSPaths(
        ca_cert=certs / "ca.pem",
        cert=certs / "server.pem",
        key=certs / "server-key.pem",
    )

    app = ServerApp(args.host, args.port, tls)
    app.start()
    try:
        run_cli(app)
    finally:
        app.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())