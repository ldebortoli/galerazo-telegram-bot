"""Persistent, conservative VM egress budget; owns only the Mini App tunnel."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from .runtime import ensure_python_version

MB = 1_000_000
WARNING_BYTES = (700 * MB, 850 * MB)
LIMIT_BYTES = 950 * MB
POLL_SECONDS = 2
# Billing documents midnight UTC-8. Fixed PST also avoids an early DST reset.
BILLING_ZONE = timezone(timedelta(hours=-8))
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Sample:
    at: float
    boot: str
    boot_started: float
    counters: dict[str, int]


@dataclass(frozen=True)
class Budget:
    period: str
    sample: Sample
    used: int
    uncertain: bool
    notified: str = ""

    @property
    def blocked(self) -> bool:
        return self.uncertain or self.used >= LIMIT_BYTES

    @property
    def notice(self) -> str:
        level = sum(self.used >= n for n in (*WARNING_BYTES, LIMIT_BYTES))
        return f"{self.period}:{'unknown' if self.uncertain else level}"


def billing_period(timestamp: float) -> tuple[str, float]:
    now = datetime.fromtimestamp(timestamp, BILLING_ZONE)
    return now.strftime("%Y-%m"), now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp()


def read_sample(root: Path = Path("/")) -> Sample:
    counters = {}
    for interface in (root / "sys/class/net").iterdir():
        if (interface / "device").exists():
            index = int((interface / "ifindex").read_text())
            counters[f"{interface.name}:{index}"] = int((interface / "statistics/tx_bytes").read_text())
    boot = (root / "proc/sys/kernel/random/boot_id").read_text().strip()
    boot_started = float(next(line.split()[1] for line in (root / "proc/stat").read_text().splitlines() if line.startswith("btime ")))
    if not boot or not counters or min(counters.values()) < 0:
        raise ValueError("No trustworthy physical NIC counters")
    return Sample(datetime.now(timezone.utc).timestamp(), boot, boot_started, counters)


def advance(previous: Budget | None, sample: Sample) -> Budget:
    period, start = billing_period(sample.at)
    total = sum(sample.counters.values())
    if previous is None:
        # All bytes since boot are an upper bound on this month's traffic, ONLY
        # when that boot predates the month. Never assume a mid-month start is 0.
        return Budget(period, sample, total, sample.boot_started > start)
    old = previous.sample
    continuous = (sample.boot == old.boot and sample.counters.keys() == old.counters.keys()
                  and all(sample.counters[k] >= v for k, v in old.counters.items()))
    delta = total - sum(old.counters.values()) if continuous else total
    backwards = sample.at < old.at
    if period != previous.period and not backwards:
        # Charge the entire boundary interval to the new month, conservatively.
        return Budget(period, sample, delta, not continuous and sample.boot_started > start, previous.notified)
    return Budget(previous.period, sample, previous.used + max(delta, 0),
                  previous.uncertain or not continuous or backwards, previous.notified)


def load_budget(path: Path) -> Budget | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        sample = Sample(**data.pop("sample"))
        budget = Budget(sample=sample, **data)
        if (type(budget.used) is not int or budget.used < 0 or type(budget.uncertain) is not bool
                or not isinstance(budget.notified, str) or not isinstance(sample.boot, str)
                or not sample.boot or not sample.counters
                or any(type(v) is not int or v < 0 for v in sample.counters.values())
                or sample.boot_started > sample.at
                or budget.period != billing_period(sample.at)[0]):
            raise ValueError("Invalid saved budget")
        return budget
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
        # Recover only by the conservative boot baseline; advance() decides if
        # history covers this month. Never zero a lost or corrupt counter.
        return None


def save_budget(path: Path, budget: Budget) -> None:
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(asdict(budget), stream, separators=(",", ":"))
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def monthly_baseline(period: str, used: int, anchor: Sample, current: Sample) -> Budget:
    """Join an audited monthly estimate to live counters, without losing tail bytes.

    Operator-only recovery: callers must verify the source/estimate, preserve a
    backup and stop the supervisor before replacing its state. No cloud calls or
    automatic resets. Unknown history still closes the tunnel in advance().
    """
    if (period != billing_period(anchor.at)[0] or period != billing_period(current.at)[0]
            or type(used) is not int or used < 0 or anchor.boot_started > anchor.at
            or not anchor.boot or not anchor.counters
            or any(type(v) is not int or v < 0 for v in anchor.counters.values())
            or current.boot_started != anchor.boot_started):
        raise ValueError("Invalid monthly baseline")
    budget = advance(Budget(period, anchor, used, False), current)
    if budget.uncertain:
        raise ValueError("Monthly baseline lost counter continuity")
    return budget


def notice_text(budget: Budget) -> str:
    limit_mb = LIMIT_BYTES // MB
    if budget.uncertain:
        status = "Mini App pausada: falta historial fiable de transferencia."
    elif budget.blocked:
        status = f"Mini App pausada: se alcanzo el corte de {limit_mb} MB."
    elif budget.used >= WARNING_BYTES[0]:
        status = f"Aviso de transferencia. La Mini App se pausa a los {limit_mb} MB."
    else:
        status = f"Monitor activo; la Mini App se pausa a los {limit_mb} MB del mes."
    return (f"{status}\nMes calendario: {budget.period} (reinicio dia 1, 08:00 UTC / 05:00 Argentina).\n"
            f"Salida VM contabilizada conservadoramente: {budget.used / MB:.2f} MB.\n"
            "Telegram sigue funcionando. Esta medicion no es una factura ni incluye otras VM.")


async def send_notice(text: str) -> bool:
    try:
        # Dedicated env file: no full bot environment or SQLite mount required.
        token = os.environ["TELEGRAM_BOT_TOKEN"]
        chat = os.environ["TELEGRAM_LOG_CHAT_ID"]
        async with httpx.AsyncClient(timeout=5, trust_env=False) as client:
            response = await client.post(f"https://api.telegram.org/bot{token}/sendMessage",
                                         json={"chat_id": chat, "text": text})
            return response.is_success and response.json().get("ok") is True
    except (KeyError, httpx.HTTPError, ValueError):
        return False


TUNNEL_COMMAND = (
    "/usr/bin/cloudflared", "tunnel", "--no-autoupdate", "--edge-ip-version", "6",
    "--protocol", "http2", "--loglevel", "warn", "--grace-period", "1s",
    "--metrics", "127.0.0.1:20241", "run", "--token-file", "/etc/galerazo/cloudflared.token",
)


class Supervisor:
    def __init__(self, path: Path):
        self.path = path
        self.budget = load_budget(path)
        self.child = None
        self.notification = None
        self.notification_key = ""
        self.retry_at = 0.0
        self.start_at = 0.0

    async def stop_tunnel(self) -> None:
        if self.child is not None:
            if self.child.returncode is None:
                try:
                    self.child.terminate()
                    await asyncio.wait_for(self.child.wait(), timeout=1)
                except TimeoutError:
                    self.child.kill()
                    await self.child.wait()
                except ProcessLookupError:
                    pass
            self.child = None

    async def step(self) -> None:
        self.budget = advance(self.budget, read_sample())
        # Persistence must succeed before opening/keeping the tunnel.
        save_budget(self.path, self.budget)
        if self.budget.blocked:
            await self.stop_tunnel()
        elif (self.child is None or self.child.returncode is not None) and self.budget.sample.at >= self.start_at:
            self.start_at = self.budget.sample.at + 30
            self.child = await asyncio.create_subprocess_exec(*TUNNEL_COMMAND,
                # Child needs only its mounted tunnel token, never the Telegram token.
                env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"},
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        if self.notification is not None and self.notification.done():
            if self.notification.result():
                self.budget = replace(self.budget, notified=self.notification_key)
                save_budget(self.path, self.budget)
            self.notification = None
        if (self.notification is None and self.budget.notified != self.budget.notice
                and (self.notification_key != self.budget.notice or self.budget.sample.at >= self.retry_at)):
            self.notification_key = self.budget.notice
            self.retry_at = self.budget.sample.at + 600
            logger.warning(notice_text(self.budget))
            # A slow Telegram response must never postpone the cutoff check.
            self.notification = asyncio.create_task(send_notice(notice_text(self.budget)))

    async def run(self, stopped: asyncio.Event) -> None:
        try:
            while not stopped.is_set():
                try:
                    await self.step()
                except Exception:
                    # No errors may leave an unmanaged tunnel alive. Docker exit
                    # also kills its entire private PID namespace on a hard crash.
                    await self.stop_tunnel()
                    logger.error("Traffic guard failed; Mini App tunnel stopped.")
                    raise
                try:
                    await asyncio.wait_for(stopped.wait(), timeout=POLL_SECONDS)
                except TimeoutError:
                    pass
        finally:
            await self.stop_tunnel()
            if self.notification is not None:
                self.notification.cancel()
                await asyncio.gather(self.notification, return_exceptions=True)


async def main() -> None:
    ensure_python_version()
    logging.basicConfig(level=logging.WARNING)
    # httpx's INFO request log would contain the Bot API token.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    stopped = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stopped.set())
    await Supervisor(Path("/var/lib/galerazo-traffic/budget.json")).run(stopped)


if __name__ == "__main__":  # pragma: no cover - delegates to the tested main
    asyncio.run(main())
