#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import re
import sqlite3
import sys
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import quote, urlencode


BOT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]$")
PREFIX_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,511}$")
METADATA_HOST = "metadata.google.internal"
STORAGE_HOST = "storage.googleapis.com"
CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class BackupConfig:
    bot_id: str
    database_path: Path
    local_backup_directory: Path
    bucket: str
    object_prefix: str
    retention_days: int


@dataclass(frozen=True)
class BackupResult:
    backup_path: Path
    checksum_path: Path
    sha256: str
    size_bytes: int
    object_name: str
    checksum_object_name: str
    completed_at: datetime


def load_config(path: Path) -> BackupConfig:
    values = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(values, dict):
        raise ValueError("Backup config must be a JSON object.")

    bot_id = _required_string(values, "botId")
    bucket = _required_string(values, "bucket")
    object_prefix = _required_string(values, "objectPrefix").strip("/")
    database_path = Path(_required_string(values, "databasePath"))
    local_backup_directory = Path(_required_string(values, "localBackupDirectory"))
    retention_days = values.get("retentionDays")

    if not BOT_ID_PATTERN.fullmatch(bot_id):
        raise ValueError("Invalid botId.")
    if not BUCKET_PATTERN.fullmatch(bucket):
        raise ValueError("Invalid Cloud Storage bucket name.")
    if not PREFIX_PATTERN.fullmatch(object_prefix) or ".." in object_prefix.split("/"):
        raise ValueError("Invalid Cloud Storage object prefix.")
    if not database_path.is_absolute() or not local_backup_directory.is_absolute():
        raise ValueError("Database and backup paths must be absolute.")
    if not isinstance(retention_days, int) or not 31 <= retention_days <= 3650:
        raise ValueError("retentionDays must be between 31 and 3650.")

    return BackupConfig(
        bot_id=bot_id,
        database_path=database_path,
        local_backup_directory=local_backup_directory,
        bucket=bucket,
        object_prefix=object_prefix,
        retention_days=retention_days,
    )


def create_consistent_backup(config: BackupConfig, now: datetime | None = None) -> BackupResult:
    completed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not config.database_path.is_file() or config.database_path.is_symlink():
        raise FileNotFoundError(f"SQLite database not found: {config.database_path}")

    config.local_backup_directory.mkdir(parents=True, exist_ok=True)
    timestamp = completed_at.strftime("%Y%m%dT%H%M%SZ")
    unique_suffix = uuid.uuid4().hex[:8]
    filename = f"{config.bot_id}-{timestamp}-{unique_suffix}.sqlite3"
    backup_path = config.local_backup_directory / filename
    partial_path = config.local_backup_directory / f".{filename}.partial"

    try:
        source_uri = f"file:{quote(str(config.database_path), safe='/:')}?mode=ro"
        with closing(sqlite3.connect(source_uri, uri=True, timeout=30)) as source:
            source.execute("PRAGMA busy_timeout=30000")
            with closing(sqlite3.connect(partial_path)) as destination:
                source.backup(destination)
        os.chmod(partial_path, 0o600)
        _assert_integrity(partial_path)
        partial_path.replace(backup_path)
    finally:
        partial_path.unlink(missing_ok=True)

    digest = _sha256(backup_path)
    checksum_path = backup_path.with_suffix(f"{backup_path.suffix}.sha256")
    checksum_path.write_text(f"{digest}  {backup_path.name}\n", encoding="ascii")
    os.chmod(checksum_path, 0o600)
    object_root = f"{config.object_prefix}/{completed_at:%Y/%m}"

    return BackupResult(
        backup_path=backup_path,
        checksum_path=checksum_path,
        sha256=digest,
        size_bytes=backup_path.stat().st_size,
        object_name=f"{object_root}/{backup_path.name}",
        checksum_object_name=f"{object_root}/{checksum_path.name}",
        completed_at=completed_at,
    )


def run_backup(
    config: BackupConfig,
    *,
    now: datetime | None = None,
    token_provider: Callable[[], str] | None = None,
    uploader: Callable[[str, str, Path, str], dict[str, object]] | None = None,
) -> dict[str, object]:
    result = create_consistent_backup(config, now)
    access_token = (token_provider or metadata_access_token)()
    upload = uploader or upload_object
    uploaded = upload(config.bucket, result.object_name, result.backup_path, access_token)
    upload(config.bucket, result.checksum_object_name, result.checksum_path, access_token)

    uploaded_size = int(str(uploaded.get("size", result.size_bytes)))
    if uploaded_size != result.size_bytes:
        raise RuntimeError("Cloud Storage reported an unexpected object size.")

    _prune_local_backups(config, result.completed_at, protected={result.backup_path, result.checksum_path})
    status = {
        "botId": config.bot_id,
        "completedAt": result.completed_at.isoformat().replace("+00:00", "Z"),
        "sizeBytes": result.size_bytes,
        "sha256": result.sha256,
        "localPath": str(result.backup_path),
        "objectUri": f"gs://{config.bucket}/{result.object_name}",
        "integrity": "ok",
    }
    _write_status(config, status)
    return status


def metadata_access_token() -> str:
    connection = http.client.HTTPConnection(METADATA_HOST, timeout=10)
    try:
        connection.request(
            "GET",
            "/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"},
        )
        response = connection.getresponse()
        body = response.read()
    finally:
        connection.close()
    if response.status != 200:
        raise RuntimeError(f"Metadata token request failed with HTTP {response.status}.")
    payload = json.loads(body.decode("utf-8"))
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Metadata server returned no access token.")
    return token


def upload_object(bucket: str, object_name: str, path: Path, access_token: str) -> dict[str, object]:
    query = urlencode(
        {
            "uploadType": "media",
            "name": object_name,
            "ifGenerationMatch": "0",
        }
    )
    request_path = f"/upload/storage/v1/b/{quote(bucket, safe='')}/o?{query}"
    connection = http.client.HTTPSConnection(STORAGE_HOST, timeout=120)
    try:
        connection.putrequest("POST", request_path)
        connection.putheader("Authorization", f"Bearer {access_token}")
        connection.putheader("Content-Type", "application/octet-stream")
        connection.putheader("Content-Length", str(path.stat().st_size))
        connection.endheaders()
        with path.open("rb") as source:
            while chunk := source.read(CHUNK_SIZE):
                connection.send(chunk)
        response = connection.getresponse()
        body = response.read()
    finally:
        connection.close()
    if response.status not in {200, 201}:
        detail = body.decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Cloud Storage upload failed with HTTP {response.status}: {detail}")
    payload = json.loads(body.decode("utf-8"))
    if payload.get("name") != object_name:
        raise RuntimeError("Cloud Storage returned an unexpected object name.")
    return payload


def _required_string(values: dict[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing string config field: {key}")
    return value.strip()


def _assert_integrity(path: Path) -> None:
    uri = f"file:{quote(str(path), safe='/:')}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=30)) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()
    if result is None or result[0] != "ok":
        raise RuntimeError("SQLite backup failed integrity_check.")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _prune_local_backups(config: BackupConfig, now: datetime, protected: set[Path]) -> None:
    cutoff = now - timedelta(days=config.retention_days)
    patterns = (
        f"{config.bot_id}-*.sqlite3",
        f"{config.bot_id}-*.sqlite3.sha256",
    )
    for pattern in patterns:
        for candidate in config.local_backup_directory.glob(pattern):
            if candidate in protected or not candidate.is_file() or candidate.is_symlink():
                continue
            modified_at = datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc)
            if modified_at < cutoff:
                candidate.unlink()


def _write_status(config: BackupConfig, status: dict[str, object]) -> None:
    status_path = config.local_backup_directory / f"last-backup-{config.bot_id}.json"
    temporary = status_path.with_suffix(".json.partial")
    try:
        temporary.write_text(json.dumps(status, ensure_ascii=True, sort_keys=True) + "\n", encoding="ascii")
        os.chmod(temporary, 0o600)
        temporary.replace(status_path)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create and upload a consistent SQLite backup.")
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        status = run_backup(load_config(args.config))
    except Exception as exc:
        print(f"BACKUP_FAILED={type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(status, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
