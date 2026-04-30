from __future__ import annotations

import subprocess
import sys


def test_server_module_can_be_run_from_src_package() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "src.rat.server", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "RAT server" in result.stdout
