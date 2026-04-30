from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI


def create_app(state_path: Path) -> FastAPI:
    app = FastAPI(title="RAT Web UI (bonus)", version="1.0.0")

    @app.get("/sessions")
    def sessions() -> dict[str, Any]:
        if not state_path.exists():
            return {"sessions": []}
        data = json.loads(state_path.read_text(encoding="utf-8"))
        sessions: list[dict[str, Any]] = data.get("sessions", [])
        return {"sessions": sessions}

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Optional web UI (bonus).")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--state", default="data/state.json")
    args = parser.parse_args()

    app = create_app(Path(args.state))
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
