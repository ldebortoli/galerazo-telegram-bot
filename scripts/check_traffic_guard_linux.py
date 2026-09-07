"""Offline Linux smoke: the real owned process dies at the exact cutoff."""
from __future__ import annotations

import asyncio
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from galerazo_bot import traffic_guard as guard


async def check() -> None:
    guard.ensure_python_version()
    with tempfile.TemporaryDirectory() as directory:
        supervisor = guard.Supervisor(Path(directory) / "budget.json")
        # No socket, credential, cloudflared binary or external message is used.
        sample = guard.Sample(1_788_804_000, "fixture", 0, {"ens4:2": 949_999_999})
        with patch.object(guard, "TUNNEL_COMMAND", (sys.executable, "-c", "import time; time.sleep(60)")), \
             patch.object(guard, "read_sample", return_value=sample) as read, \
             patch.object(guard, "send_notice", AsyncMock(return_value=True)):
            try:
                await supervisor.step()
                process = supervisor.child
                assert process is not None and process.returncode is None
                await supervisor.notification
                read.return_value = replace(sample, counters={"ens4:2": 950_000_000})
                await supervisor.step()
                assert supervisor.child is None and process.returncode is not None
                assert guard.load_budget(supervisor.path).blocked
                await supervisor.notification
                read.return_value = replace(sample, at=1_793_491_200, counters={"ens4:2": 950_000_010})
                await supervisor.step()
                assert supervisor.child is not None
                assert not guard.load_budget(supervisor.path).blocked
            finally:
                await supervisor.stop_tunnel()
                if supervisor.notification is not None:
                    await supervisor.notification
    print("Linux guard smoke OK: real process stopped at 950 MB, state persisted, new month resumed.")


if __name__ == "__main__":
    asyncio.run(check())
