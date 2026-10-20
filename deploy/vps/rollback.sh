#!/usr/bin/env bash
# Manual image rollback preserves the live database; keep a fresh backup first.
set -Eeuo pipefail
umask 077
cd /opt/galerazo
test -s previous-image.env
previous="$(sed -n 's/^GALERAZO_IMAGE=//p' previous-image.env)"
exec /opt/galerazo/deploy.sh "$previous"
