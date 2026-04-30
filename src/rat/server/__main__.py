from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ == "src.rat.server":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rat.core.tls import TLSPaths  # noqa: E402
from rat.server.app import ServerApp  # noqa: E402
from rat.server.cli import run_cli  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="RAT server (TLS, multi-agents, interactive CLI).")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8888, help="Bind port (default: 8888)")
    parser.add_argument("--certs", default="certs", help="Certificates directory (default: certs)")
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
