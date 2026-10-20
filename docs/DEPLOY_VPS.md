# Contabo deployment and database backups

Production uses the existing Contabo host with Ubuntu 24.04, Docker's systemd
cgroup driver and cgroup v2. Do not activate GCP billing, a registry, paid backup,
new hosting or capacity upgrades without Lucas's explicit request.

## Limits and network

`deploy/vps/bootstrap.sh` installs the versioned slices. `apps.slice` has a 6 GiB
aggregate ceiling, leaving memory for Ubuntu and Docker on the 8 GB host.
Galerazo's complete stack belongs to `apps-galerazo.slice` (2 GiB): the bot has
1792 MiB and cloudflared 128 MiB. Swap is disabled for these workloads.
Tivio, A la Altura and En la misma each have a 1 GiB aggregate slice, including
their database and auxiliary processes. Every future application requires its
own slice with at most 2 GiB; do not rely only on an API container limit.

The bot polls Telegram outbound. Its Mini App API listens on `127.0.0.1:8080`.
The existing Cloudflare tunnel serves `bot-api.galerazo.com`; its metrics also
bind to loopback. Keep databases and administrative endpoints off public ports.
The public frontend remains on its existing Cloudflare Worker. The Worker and
backend require the same private proxy secret plus valid Telegram initData.

## Local deployment

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
./scripts/deploy/Invoke-VpsBot.ps1 -VpsConfigFile $target -Action rollback
```

Publication validates runtime and the approved release announcement, runs the
Docker test target, builds the runtime and transfers a local image archive by
SSH. No external registry is used. The archive is removed after Docker loads it.
The tag normally identifies the selected Git commit. Deploy validates the local
image and database, stops the old bot, takes a consistent pre-deploy snapshot,
starts one candidate and waits for health. A failed candidate is stopped before
restoring the pre-deploy database and restarting the previous image. Manual
rollback takes a fresh snapshot and preserves the current database; schema
compatibility still needs review before choosing an older image.

The frontend bridge checks backend health over this same strict SSH transport.
Its source must be clean, on `main`, and from the expected remote; publication
uses an immutable worktree and verifies served metadata, assets and closed
anonymous API access. Never publish unrelated edits from another active task.

## Daily backups

`codex-backup@<app>.timer` runs daily at 04:00 Argentina, with up to 20 minutes
jitter and `Persistent=true` for missed runs. A host-wide flock serializes jobs;
`apps-backups.slice` caps all backup jobs together at 512 MiB. Root-owned 0600
configuration lives in `/etc/codex-backups/<app>.conf`. The common private
Telegram environment is `/etc/codex-backups/telegram.env`.

SQLite uses the backup API, including committed WAL, then `integrity_check`.
PostgreSQL configurations set `BACKUP_FORMAT=dump` and `DATABASE_CONTAINER`;
the runner executes `pg_dump -Fc` with the database container's existing private
environment and checks `pg_restore --list`. Each PostgreSQL project must also
verify a real restore into an isolated database; archive listing alone is not a
complete restore test.

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
Existing files for the current Argentina date are reused for retries, so a
manual second run that day verifies the same snapshot. Do not overwrite a
confirmed artifact/receipt to force another backup; use a distinct timestamp.

```sh
systemctl start codex-backup@galerazo.service
systemctl status codex-backup@galerazo.service
systemctl list-timers 'codex-backup@*'
journalctl -u codex-backup@galerazo.service --since today
```

For SQLite restore: stop the bot, verify the selected receipt/hash and SQLite
integrity, preserve the current database, replace it with the selected snapshot,
remove stale WAL/SHM while stopped, set owner 10001 and mode 0600, then start and
verify health and Telegram. Restoring an old backup discards later writes; select
the restore point explicitly. Never test a restore over the live production DB.

## Validation

Run `.venv/Scripts/python.exe scripts/runtime_versions.py`, then coverage:
`python -m coverage run -m pytest`, `python -m coverage json` and
`python scripts/check_coverage.py`. Python deployment/credential helpers are
included in the 100% statement/branch gate. PowerShell and bash adapters are
validated with their parsers and real host smoke checks; Python coverage does
not instrument those interpreters. Docker dependency changes also require the
test target. Remote CI is not monitored after pushing.

`scripts/test_vps_deploy.sh` is an opt-in Linux integration harness for an
ephemeral `python:3.14.8-slim` container with network disabled. Mount `deploy/vps`
at `/fixture` and this harness plus `telegram_backup.py` under `/input` as
read-only files. It fakes Docker commands while exercising actual SQLite
snapshots and rollback for first deploy, successful upgrade, a failed candidate
that wrote to the DB, and a failed snapshot. Never run this fixture on a real
host: its fixed `/opt` and `/srv` paths belong only to the disposable container.
