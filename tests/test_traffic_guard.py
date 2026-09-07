from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from galerazo_bot import traffic_guard as g


def sample(at="2026-09-07T18:00:00+00:00", used=100, boot="a", boot_started=0):
    return g.Sample(datetime.fromisoformat(at).timestamp(), boot, boot_started, {"ens4:2": used})


@pytest.mark.parametrize("used,blocked,level", [(0, False, 0), (699999999, False, 0),
    (700000000, False, 1), (849999999, False, 1), (850000000, False, 2),
    (924999999, False, 2), (925000000, True, 3), (1100000000, True, 3)])
def test_exact_thresholds(used, blocked, level):
    budget = g.advance(None, sample(used=used))
    assert budget.used == used
    assert budget.blocked is blocked
    assert budget.notice == f"2026-09:{level}"
    assert "Telegram sigue funcionando" in g.notice_text(budget)


def test_month_rollover_does_not_reset_at_utc_midnight_or_early_in_summer():
    previous = g.advance(None, sample("2026-09-30T23:59:59+00:00", 950000000))
    for at in ("2026-10-01T00:00:00+00:00", "2026-10-01T07:59:59+00:00"):
        previous = g.advance(previous, sample(at, 950000020))
        assert previous.period == "2026-09" and previous.blocked
    current = g.advance(previous, sample("2026-10-01T08:00:00+00:00", 950000050))
    assert current.period == "2026-10"
    assert current.used == 30 and not current.blocked


def test_first_install_unknown_history_and_counter_discontinuities_stay_closed():
    late_boot = sample(boot_started=sample().at - 100)
    uncertain = g.advance(None, late_boot)
    assert uncertain.uncertain and uncertain.blocked
    assert "falta historial" in g.notice_text(uncertain)
    assert uncertain.notice.endswith("unknown")
    old = g.advance(None, sample(used=1000))
    for discontinuity in (sample(used=10), sample(boot="b"),
                          replace(sample(), counters={"ens4:3": 1000}),
                          sample("2026-09-06T18:00:00+00:00")):
        paused = g.advance(old, discontinuity)
        assert paused.blocked and paused.used >= 1000
        assert g.advance(paused, sample()).uncertain
    # Across a reboot with missing end-of-month data, keep the new month closed
    # unless the new boot predates that month (then count ALL boot traffic).
    new = sample("2026-10-02T18:00:00+00:00", boot="b")
    assert not g.advance(old, new).blocked
    assert g.advance(old, replace(new, boot_started=new.at - 10)).blocked
    # Unknown September history can recover with a continuous October sample.
    assert not g.advance(uncertain, replace(new, boot="a", boot_started=late_boot.boot_started)).blocked


def test_restart_persists_notice_and_charges_bytes_while_monitor_was_down(tmp_path):
    path = tmp_path / "budget.json"
    budget = replace(g.advance(None, sample()), notified="2026-09:0")
    g.save_budget(path, budget)
    assert g.load_budget(path) == budget
    current = g.advance(g.load_budget(path), sample(used=500))
    assert current.used == 500 and current.notified == "2026-09:0"
    assert not path.with_suffix(".tmp").exists()
    with patch.object(g.os, "fsync", side_effect=OSError):
        with pytest.raises(OSError):
            g.save_budget(path, current)
    assert g.load_budget(path) == budget


@pytest.mark.parametrize("value", [None, "bad json", [], {}, {"sample": {}},
    {"used": -1}, {"used": True}, {"uncertain": 0}, {"notified": None},
    {"period": "2020-01"}, {"sample": {"boot": ""}}, {"sample": {"counters": {}}},
    {"sample": {"counters": {"eth0": -1}}}, {"sample": {"boot_started": 9e20}}])
def test_lost_or_corrupt_file_never_produces_a_zero_baseline(tmp_path, value):
    path = tmp_path / "budget.json"
    if value is not None:
        if isinstance(value, dict) and value:
            data = asdict(g.advance(None, sample()))
            if "sample" in value:
                data["sample"].update(value["sample"])
            else:
                data.update(value)
            # Empty sample is an intentionally malformed document.
            if value == {"sample": {}}:
                data = value
            value = data
        path.write_text(value if isinstance(value, str) else json.dumps(value))
    assert g.load_budget(path) is None
    assert g.advance(g.load_budget(path), sample(used=800000000)).used == 800000000


def test_reads_only_physical_nic_and_detects_invalid_readings(tmp_path):
    for name, physical, value in (("ens4", True, "750"), ("lo", False, "900"), ("veth0", False, "800")):
        interface = tmp_path / "sys/class/net" / name
        (interface / "statistics").mkdir(parents=True)
        if physical:
            (interface / "device").mkdir()
        (interface / "ifindex").write_text("2")
        (interface / "statistics/tx_bytes").write_text(value)
    proc = tmp_path / "proc"
    (proc / "sys/kernel/random").mkdir(parents=True)
    boot = proc / "sys/kernel/random/boot_id"
    boot.write_text("test-boot\n")
    (proc / "stat").write_text("cpu 1 2 3\nbtime 100\n")
    assert g.read_sample(tmp_path).counters == {"ens4:2": 750}
    boot.write_text("")
    with pytest.raises(ValueError):
        g.read_sample(tmp_path)
    boot.write_text("test")
    (tmp_path / "sys/class/net/ens4/statistics/tx_bytes").write_text("-1")
    with pytest.raises(ValueError):
        g.read_sample(tmp_path)
    (tmp_path / "sys/class/net/ens4/device").rmdir()
    with pytest.raises(ValueError):
        g.read_sample(tmp_path)


@pytest.mark.asyncio
async def test_notification_http_and_errors_never_log_credentials():
    for status, payload, expected in ((200, {"ok": True}, True), (200, {"ok": False}, False), (429, {}, False)):
        client = AsyncMock()
        client.post.return_value = httpx.Response(status, json=payload)
        with patch.dict(g.os.environ, {"TELEGRAM_BOT_TOKEN": "private", "TELEGRAM_LOG_CHAT_ID": "logs"}), \
             patch.object(g.httpx, "AsyncClient") as factory:
            factory.return_value.__aenter__.return_value = client
            assert await g.send_notice("test") is expected
            assert client.post.call_args.kwargs["json"]["chat_id"] == "logs"
    with patch.dict(g.os.environ, {}, clear=True):
        assert not await g.send_notice("test")
    for error in (httpx.ConnectError("private"), ValueError("invalid JSON")):
        with patch.dict(g.os.environ, {"TELEGRAM_BOT_TOKEN": "private", "TELEGRAM_LOG_CHAT_ID": "logs"}), \
             patch.object(g.httpx, "AsyncClient", side_effect=error):
            assert not await g.send_notice("test")


def child():
    return Mock(returncode=None, wait=AsyncMock(return_value=0))


@pytest.mark.asyncio
async def test_cutoff_precedes_slow_notification_and_is_persistent(tmp_path):
    s = g.Supervisor(tmp_path / "budget.json")
    process = child()
    gate = asyncio.Event()
    async def slow_notice(_text):
        await gate.wait()
        return True
    with patch.object(g, "read_sample", return_value=sample(used=700000000)) as reading, \
         patch.object(g.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)) as spawn, \
         patch.object(g, "send_notice", slow_notice):
        await s.step()
        assert spawn.call_count == 1
        assert "TELEGRAM_BOT_TOKEN" not in spawn.call_args.kwargs["env"]
        await s.step()  # pending notice must not start another child or notice
        reading.return_value = sample(used=925000000)
        await s.step()
        process.terminate.assert_called_once()
        assert g.load_budget(s.path).blocked
        assert not s.notification.done()
        gate.set()
        await s.notification
        await s.step()
        assert g.load_budget(s.path).notified == "2026-09:1"
        # A new severity bypasses cooldown after the earlier notice finishes.
        await s.notification
        await s.step()
        assert g.load_budget(s.path).notified == "2026-09:3"
        assert s.notification is None
        assert spawn.call_count == 1


@pytest.mark.asyncio
async def test_notification_failure_retries_and_dead_tunnel_has_backoff(tmp_path):
    s = g.Supervisor(tmp_path / "budget.json")
    process = child()
    with patch.object(g, "read_sample", return_value=sample()) as reading, \
         patch.object(g.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)) as spawn, \
         patch.object(g, "send_notice", AsyncMock(return_value=False)) as notify:
        await s.step()
        await s.notification
        process.returncode = 1
        await s.step()
        assert s.notification is None and notify.call_count == 1
        assert spawn.call_count == 1
        reading.return_value = sample("2026-09-07T18:10:01+00:00", 1000)
        await s.step()
        assert spawn.call_count == 2
        await s.notification
        await s.step()
        assert notify.call_count == 2
        await s.stop_tunnel()


@pytest.mark.asyncio
async def test_stuck_or_already_exited_child_cannot_survive_stop(tmp_path):
    s = g.Supervisor(tmp_path / "budget.json")
    s.child = child()
    process = s.child
    process.wait.side_effect = [TimeoutError, 0]
    await s.stop_tunnel()
    process.kill.assert_called_once()
    s.child = child()
    s.child.terminate.side_effect = ProcessLookupError
    await s.stop_tunnel()
    assert s.child is None


@pytest.mark.asyncio
async def test_unreadable_counter_or_unwritable_state_stops_existing_tunnel(tmp_path):
    s = g.Supervisor(tmp_path / "budget.json")
    s.child = child()
    process = s.child
    with patch.object(g, "read_sample", side_effect=OSError("unreadable")):
        with pytest.raises(OSError):
            await s.run(asyncio.Event())
    process.terminate.assert_called_once()
    with patch.object(g, "read_sample", return_value=sample()), \
         patch.object(g, "save_budget", side_effect=OSError("disk full")), \
         patch.object(g.asyncio, "create_subprocess_exec", AsyncMock()) as spawn:
        with pytest.raises(OSError):
            await s.run(asyncio.Event())
        spawn.assert_not_called()


@pytest.mark.asyncio
async def test_run_wait_shutdown_and_main_signals(tmp_path):
    s = g.Supervisor(tmp_path / "budget.json")
    stopped = asyncio.Event()
    async def step():
        if s.step.call_count == 2:
            stopped.set()
        if s.notification is None:
            s.notification = asyncio.create_task(asyncio.sleep(30))
    with patch.object(s, "step", AsyncMock(side_effect=step)) as tick, patch.object(g, "POLL_SECONDS", 0.001):
        await s.run(stopped)
    assert tick.call_count == 2
    await s.run(stopped)
    fresh = g.Supervisor(tmp_path / "empty.json")
    await fresh.run(stopped)
    with patch.object(g, "ensure_python_version"), patch.object(g, "Supervisor") as supervisor, \
         patch.object(g.signal, "signal") as handler:
        supervisor.return_value.run = AsyncMock()
        await g.main()
        handler.call_args.args[1]()
        assert supervisor.return_value.run.call_args.args[0].is_set()
