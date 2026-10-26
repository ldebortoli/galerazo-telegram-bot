# Contabo deployment and database backups

Production uses the existing Contabo host with Ubuntu 24.04, Docker's systemd
cgroup driver and cgroup v2. Do not activate a registry, paid backup,
new hosting or capacity upgrades without Lucas's explicit request.

## Limits and network

`deploy/vps/bootstrap.sh` installs the versioned slices. `apps.slice` has a 6 GiB
aggregate ceiling, leaving memory for Ubuntu and Docker on the 8 GB host.
Galerazo's complete stack belongs to `apps-galerazo.slice` (1 GiB): the bot has
768 MiB and cloudflared 128 MiB, leaving 128 MiB for deployment preflight.
Swap is disabled for these workloads. Lucas reduced Galerazo's aggregate ceiling
from 2 GiB to 1 GiB on 2026-10-20; older deployment receipts retain the old limit.
Tivio, A la Altura and En la misma each have a 1 GiB aggregate slice, including
their database and auxiliary processes. Every future application requires its
own slice with at most 2 GiB; do not rely only on an API container limit.

The bot polls Telegram outbound. Its Mini App API listens on `127.0.0.1:8080`.
The existing Cloudflare tunnel serves `bot-api.galerazo.com`; its metrics also
bind to loopback. Keep databases and administrative endpoints off public ports.

The independent tunnel stack pins `cloudflare/cloudflared:2026.10.3`, following
Cloudflare's October 2026 Docker update notice. Its 35-second stop timeout covers
cloudflared's default 30-second request grace period. For an authorized update,
hold the existing Bot Control Center operation lock and server deployment lock,
start a temporary replica in the same application slice with separate loopback
metrics, and verify readiness and Cloudflare connectivity before replacing the
original connector. Verify the original is healthy on the new image before
removing the temporary replica. Keep the previous image for rollback and preserve
the bot, origin configuration, TLS verification, tokens and resource limits.
Long-lived sessions on a replaced connector may need to reconnect.
The public frontend remains on its existing Cloudflare Worker. The Worker and
backend require the same private proxy secret plus valid Telegram initData.

## Local deployment

The verified rollout on 2026-10-20 runs bot 0.80 (`galerazo-bot:ee2aba412e2b`)
and frontend 0.1.27 through Bot Control Center 0.1.7. Galerazo's operational
configuration and catalog examples select only Contabo/SSH. The existing monthly task uses this same configuration.
The rollout passed its joint verification, database integrity and isolated
snapshot restore checks. Nine other containers retained their IDs, images,
start times, restart counters and limits; host port bindings were unchanged.
The verified previous bot image remains available for an authorized rollback.

Use Bot Control Center's existing Deploy view for normal operations: verify the
target, then choose the explicitly authorized release, deployment or rollback.
Its manager and per-bot operation lock cover the complete bot/frontend workflow.
The server also serializes deployments with `/run/lock/galerazo-deploy.lock`.
The adapter commands below are maintainer references, not a sequence to run when
reading this guide. An ordinary fix, documentation update or push does not
authorize a deployment.

Bot Control Center uses `provider: "vps"` and a local `vpsConfigFile`. The JSON
contains `host`, `user`, `identityFile` and `knownHostsFile`, with paths to
existing private files. Keep it under ignored `deploy/out/`; never version keys,
tokens, passwords, databases or live environment files. Restrict private keys to
the owning Windows user and SYSTEM. SSH requires strict host-key checking,
batch mode and an explicit identity; an unknown or changed host key stops it.

The existing manager and operation lock call `scripts/deploy/Invoke-VpsBot.ps1`:

```powershell
$target = Join-Path $PWD 'deploy/out/vps-target.json'
./scripts/deploy/Invoke-VpsBot.ps1 -VpsConfigFile $target -Action publish
$image = (Get-Content deploy/out/last-image.txt -Raw).Trim()
./scripts/deploy/Invoke-VpsBot.ps1 -VpsConfigFile $target -Action deploy -Image $image
./scripts/deploy/Invoke-VpsBot.ps1 -VpsConfigFile $target -Action status
```

The Windows wrapper runs Python with `-X utf8` so remote Unicode output works
with Windows console encodings. Do not remove this argument. The local `.env`
can belong to the test bot; production uses `/etc/galerazo/bot.env` and its
existing private credentials. Never replace it with the local test environment.

Publication validates runtime and the approved release announcement, runs the
Docker test target, builds the runtime and transfers a local image archive by
SSH. No external registry is used. The archive is removed after Docker loads it.
The tag normally identifies the selected Git commit. Deploy validates the local
image and database, stops the old bot, takes a consistent pre-deploy snapshot,
starts one candidate and waits for health. A failed candidate is stopped before
restoring the pre-deploy database and restarting the previous image. Manual
rollback takes a fresh snapshot and preserves the current database; schema
compatibility still needs review before choosing an older image.

`/opt/galerazo/image.env` identifies the selected image; the Docker container's
actual image and state establish what is running. `deploy/out/last-image.txt`
records publication locally and does not prove a successful deployment.

The first deployment has no previous image. `rollback.sh` requires a nonempty
`/opt/galerazo/previous-image.env` and stops if it is absent. A later deployment
with a different existing image copies that reference before starting its
candidate; verify both the file and the locally available image before rollback:

```powershell
./scripts/deploy/Invoke-VpsBot.ps1 -VpsConfigFile $target -Action rollback
```

A failed first candidate can restore its pre-deploy database after being stopped,
but cannot restart a nonexistent previous image. If stopping a failed candidate
fails, deployment leaves the database intact and requires operator recovery.
Never manufacture a previous-image reference from an unverified tag. Manual image rollback keeps current data
on success; restoring an older database is a separate, explicitly chosen action.

The frontend bridge checks backend health over this same strict SSH transport.
Its source must be clean, on `main`, and from the expected remote; publication
uses an immutable worktree and verifies served metadata, assets and closed
anonymous API access. Never publish unrelated edits from another active task.

The existing monthly Windows release remains on day 1 at 03:00 Argentina, with
12 hourly retries, a three-hour limit and `IgnoreNew`. It uses this same manager,
configuration and lock; do not create a second scheduler. It requires the PC and
the Windows user session. The daily server backup is independent of that PC.

## Health and installed files

Docker's `galerazo_bot.healthcheck` opens SQLite read-only and runs `SELECT 1`.
`healthy` proves database readability, not Telegram connectivity, processing of
updates, database integrity or end-user Mini App QA. Bot Control Center status
also checks the active image, restarts, recent logs and Telegram `getMe`. Check
real update processing and errors/conflicts in existing logs separately; never
start a second polling process to test production.

Check the effective cgroup values, not just Compose declarations:

```sh
systemctl show apps.slice apps-galerazo.slice apps-backups.slice -p Id -p MemoryMax -p MemorySwapMax
cat /sys/fs/cgroup/apps.slice/apps-galerazo.slice/memory.max
cat /sys/fs/cgroup/apps.slice/apps-galerazo.slice/memory.swap.max
```

Galerazo's aggregate ceiling must read `1073741824` and swap `0`. Verify the bot,
the separate `deploy/vps/tunnel.yaml` stack and any preflight container all use
`apps-galerazo.slice`. The bot and tunnel limits are 768 MiB and 128 MiB; the
offline database preflight has 128 MiB. Maximums are ceilings, not reservations;
reassess the shared host budget before adding another application.

| Server path | Purpose |
| --- | --- |
| `/opt/galerazo/compose.yaml` | Generated merge of the base and VPS bot Compose files |
| `/opt/galerazo/image.env`, `previous-image.env` | Selected and previous image references |
| `/opt/galerazo/tunnel.yaml` | Independently managed existing tunnel stack |
| `/etc/galerazo/` | Private production bot environment, tunnel token and Sheets credential |
| `/srv/galerazo/data/galerazo.sqlite3` | Live production database |
| `/srv/galerazo/backups/predeploy-*.sqlite3` | Deployment recovery snapshots |
| `/opt/codex-backups/venv`, `telegram_backup.py` | Shared backup runtime and delivery helper |
| `/usr/local/sbin/codex-database-backup` | Installed `deploy/vps/database-backup.sh` runner |
| `/srv/codex-backups/galerazo/` | Daily artifacts and durable delivery receipts |

`bootstrap.sh` prepares prerequisites and slices; it does not by itself install
the backup runtime, runner, timer, private configuration or tunnel stack. The
existing server has these installed. A future rebuild must explicitly restore
those components and validate them. Keep private installation evidence and
delivery receipts outside Git; refer to their locations instead of copying keys
or environments into a runbook. Never publish full `docker inspect` output,
which includes container environment variables.

## Daily backups

The active schedule is `codex-backup@daily.timer`: 04:00 Argentina plus up to
20 minutes of jitter. It replaces the four disabled per-application timers;
never re-enable those timers as part of a normal Galerazo deployment. The grouped
runner belongs to the private [codex-vps-monitor repository](https://github.com/ldebortoli/codex-vps-monitor)
(source `e4283cd`, documentation closure `01d4d00`). Galerazo's older versioned
single-app installer is a recovery reference, not the active daily schedule.
All backup work shares `apps-backups.slice` (512 MiB, swap disabled).

Galerazo sends its original SQLite file to **Codex - Logs**. Tivio, A la Altura
and En la misma send an album of three original database documents to
**Apps para tu Vecina**, using the existing private target configuration. No tar/zip: each file is directly
downloadable and carries ART/UTC timestamps and its SHA-256. Consistency is per
database, not one transaction across the four applications.

SQLite uses the backup API, including committed WAL, then `integrity_check`.
PostgreSQL configurations set `BACKUP_FORMAT=dump` and `DATABASE_CONTAINER`;
the runner executes `pg_dump -Fc` with the database container's existing private
environment and checks `pg_restore --list`. Each PostgreSQL project must also
verify a real restore into an isolated database; archive listing alone is not a
complete restore test. PostgreSQL restores use the existing local image with
no network/ports, `--pull=never`, 384 MiB, swap disabled and CPU0.5 inside the
shared 512 MiB backup slice. Settings constrain buffers32MB, work_mem4MB,
maintenance32MB, max_connections10 and jitoff. Wait for final PostgreSQL PID1
as well as readiness. Clean up temporary containers and volumes even on failure.

`galerazo_bot/telegram_backup.py` verifies Codex Bot's exact identity, target
supergroup and administrator membership before sending to Codex - Logs. It
uses MTProto with disk streaming, supporting artifacts up to 2000 MiB without
logging out the shared cloud Bot API. Larger artifacts fail explicitly; add
chunking or a separately approved destination before exceeding that ceiling.
Confirmed message IDs and hashes are persisted before downloading the Telegram
copy, comparing SHA-256 and checking SQLite integrity. Retries resume the
download instead of uploading again when a confirmation receipt exists. A
process crash before saving Telegram's response remains an ambiguous-send case.

Only verified success triggers local cleanup of artifacts older than 14 days.
Existing files for the current Argentina date are reused for retries. A matching
verified receipt returns the saved success without a new upload or download;
a confirmed but unverified receipt resumes downloading that message. Do not
overwrite a confirmed artifact/receipt to force another backup; use a distinct
timestamp.

The first command below starts a delivery and is for an authorized backup or
recovery, not a health probe. Use the remaining commands for observation:

```sh
systemctl start codex-backup@daily.service
systemctl status codex-backup@daily.service
systemctl list-timers 'codex-backup@*'
journalctl -u codex-backup@daily.service --since today
```

The 2026-10-20 handoff records all four copies downloaded/hash/restore verified.
Message IDs and hashes remain in the private durable receipts; this documentation
is not an instruction to resend. Reassess disk capacity
and retention as databases grow; do not purchase capacity or raise app limits.

## Native monitoring

The VPS monitor checks every 5 minutes and sends a grouped daily summary at 09:00 ART
to Codex - Logs, with transition/recovery alerts and at most one message per check.
It observes effective limits, swap, RAM, sampled peaks, OOM/restarts, health, disk
and backup freshness. Its own ceiling is 128 MiB/CPU20%/swap0. Stable conditions do
not repeat alerts; sampled peaks do not represent continuous measurement.

Windows task `Codex - VPS daily liveness` performs one strict-host-key SSH probe
at 09:15 ART through a hidden native launcher, without AI/tokens. It requires the PC
and user session. The former Codex VPS audit automation was deleted: do not
recreate AI polling or a duplicate scheduler.

## Restore reference

For SQLite restore: stop the bot, verify the selected receipt/hash and SQLite
integrity, preserve the current database, replace it with the selected snapshot,
remove stale WAL/SHM while stopped, set owner 10001 and mode 0600, then start and
verify health and Telegram. Restoring an old backup discards later writes; select
the restore point explicitly. Never test a restore over the live production DB.

For a restore drill, use a disposable path/database, open the restored SQLite
copy, check `integrity_check` and `foreign_key_check`, and compare its expected
tables, row counts and content against the selected snapshot. Record that
evidence separately from successful download verification. A past verified
delivery must not be resent merely to learn the procedure. Preserve the
production `release_state` cursor; resetting it can duplicate an announcement.

## Validation

Run `.venv/Scripts/python.exe scripts/runtime_versions.py`, then coverage:
`.venv/Scripts/python.exe -m coverage run -m pytest`,
`.venv/Scripts/python.exe -m coverage json` and
`.venv/Scripts/python.exe scripts/check_coverage.py`. Python deployment/credential
helpers are included in the 100% statement/branch gate. PowerShell and bash adapters are
validated with their parsers and real host smoke checks; Python coverage does
not instrument those interpreters. Docker dependency changes also require the
test target. Remote CI is not monitored after pushing.

Documentation-only learning can reuse the same source's recorded full coverage
and Docker/restore results, with runtime and focused offline tests. Do not repeat
heavy suites, real Telegram sends or live restores only to learn. Report fresh
checks and reused historical evidence separately. Real Telegram QA of shared
albums and returning to the owner's album still requires a current user session
and valid initData; local fixtures or anonymous 401 responses do not complete it.

`scripts/test_vps_deploy.sh` is an opt-in Linux integration harness for an
ephemeral `python:3.14.8-slim` container with network disabled. Mount `deploy/vps`
at `/fixture` and this harness plus `telegram_backup.py` under `/input` as
read-only files. It fakes Docker commands while exercising actual SQLite
snapshots and rollback for first deploy, successful upgrade, a failed candidate
that wrote to the DB, and a failed snapshot. Never run this fixture on a real
host: its fixed `/opt` and `/srv` paths belong only to the disposable container.
