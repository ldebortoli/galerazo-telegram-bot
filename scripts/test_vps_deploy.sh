#!/usr/bin/env bash
# Opt-in local Linux integration test. Run only in an ephemeral container:
# mount deploy/vps at /fixture and telegram_backup.py at /input/telegram_backup.py.
# Docker actions are faked; SQLite snapshots and rollback are real.
set -Eeuo pipefail
install -d /opt/galerazo /opt/codex-backups/venv/bin /srv/galerazo/data /srv/galerazo/backups /etc/galerazo
ln -s /usr/local/bin/python /opt/codex-backups/venv/bin/python
cp /input/telegram_backup.py /opt/codex-backups/telegram_backup.py
printf 'TELEGRAM_BOT_TOKEN=offline-fixture\n' >/etc/galerazo/bot.env
touch /opt/galerazo/compose.yaml
cat >/usr/local/bin/docker <<'DOCKER'
#!/bin/bash
set -eu
printf '%s\n' "$*" >>/tmp/docker-calls
if [[ " $* " == *' up '* && "${FAIL_CANDIDATE:-no}" == yes ]] && grep -q new /opt/galerazo/image.env; then
  python - <<'PY'
import sqlite3
with sqlite3.connect('/srv/galerazo/data/galerazo.sqlite3') as conn:
    conn.execute("INSERT INTO records VALUES('candidate-write')")
PY
  exit 1
fi
DOCKER
chmod 0755 /usr/local/bin/docker
for scenario in first success candidate-fails snapshot-fails; do
  python - <<'PY'
from pathlib import Path
import sqlite3
for folder in ('/srv/galerazo/data','/srv/galerazo/backups'):
    for file in Path(folder).iterdir(): file.unlink()
with sqlite3.connect('/srv/galerazo/data/galerazo.sqlite3') as conn:
    conn.execute('CREATE TABLE records(value TEXT NOT NULL)')
    conn.execute("INSERT INTO records VALUES('before')")
for file in ('image.env','previous-image.env'):
    (Path('/opt/galerazo')/file).unlink(missing_ok=True)
PY
  : >/tmp/docker-calls
  export FAIL_CANDIDATE=no
  if [[ "$scenario" != first ]]; then printf 'GALERAZO_IMAGE=galerazo-bot:old\n' >/opt/galerazo/image.env; fi
  if [[ "$scenario" == candidate-fails ]]; then export FAIL_CANDIDATE=yes; fi
  if [[ "$scenario" == snapshot-fails ]]; then printf invalid >/srv/galerazo/data/galerazo.sqlite3; fi
  set +e
  bash /fixture/deploy.sh galerazo-bot:new >/tmp/result 2>&1
  result=$?
  set -e
  if [[ "$scenario" == *-fails ]]; then
    test "$result" == 1
    grep -q 'GALERAZO_IMAGE=galerazo-bot:old' /opt/galerazo/image.env
    grep -q ' up ' /tmp/docker-calls
  else
    test "$result" == 0
    grep -q 'GALERAZO_IMAGE=galerazo-bot:new' /opt/galerazo/image.env
  fi
  if [[ "$scenario" == snapshot-fails ]]; then
    test "$(cat /srv/galerazo/data/galerazo.sqlite3)" == invalid
  else
    python - <<'PY'
import sqlite3
with sqlite3.connect('/srv/galerazo/data/galerazo.sqlite3') as conn:
    assert conn.execute('SELECT value FROM records').fetchall()==[('before',)]
    assert conn.execute('PRAGMA integrity_check').fetchone()==('ok',)
PY
  fi
  echo "VPS deployment scenario passed: $scenario"
done
