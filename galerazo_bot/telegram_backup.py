"""Consistent database snapshots and verified large-file delivery to Codex Logs."""
from __future__ import annotations

from contextlib import closing
import argparse
import asyncio
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys


LOG_CHAT_ID = -1004440313456
MAX_FILE_BYTES = 2000 * 1024 * 1024


@dataclass(frozen=True)
class BackupIdentity:
    token: str = field(repr=False)
    api_id: int
    api_hash: str = field(repr=False)


def snapshot_sqlite(source: Path, target: Path) -> None:
    """Read the live database with SQLite's backup API, including committed WAL."""
    if not source.is_file():
        raise FileNotFoundError('Source database is missing.')
    if target.exists():
        raise FileExistsError('A snapshot already exists at the destination.')
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + '.partial')
    try:
        with closing(sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True, timeout=30)) as live:
            with closing(sqlite3.connect(partial)) as copy:
                live.backup(copy)
                if copy.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                    raise ValueError('Snapshot integrity check failed.')
        os.chmod(partial, 0o600)
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)


def checksum(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save_receipt(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.partial')
    temporary.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
    os.chmod(temporary, 0o600)
    temporary.replace(path)


async def deliver(path: Path, identity: BackupIdentity, receipt_path: Path, *, api, transport, max_bytes=MAX_FILE_BYTES) -> dict:
    """Use Codex Bot via MTProto; no cloud Bot API logout or polling changes."""
    size = path.stat().st_size
    if path.suffix not in {'.sqlite3', '.dump', '.gz', '.zip'} or size > max_bytes:
        raise ValueError('Not a supported database artifact, or larger than the configured file limit.')
    digest = checksum(path)
    previous = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    matching = previous.get('sha256') == digest and previous.get('chatId') == LOG_CHAT_ID
    if matching and previous.get('verified'):
        return previous
    bot = await api.get_me()
    if not bot.is_bot or bot.username != 'codexgalerazobot' or bot.first_name != 'Codex Bot':
        raise ValueError('Backup identity must be Codex Bot @codexgalerazobot.')
    chat = await api.get_chat(LOG_CHAT_ID)
    member = await api.get_chat_member(LOG_CHAT_ID, bot.id)
    if (chat.id != LOG_CHAT_ID or chat.title != 'Codex - Logs' or chat.type != 'supergroup'
            or member.status not in {'administrator', 'creator'}):
        raise ValueError('Codex Logs identity or administrator access is not valid.')
    restore = path.with_suffix('.restore')
    try:
        await transport.connect()
        remote_bot = await transport.sign_in(bot_token=identity.token)
        if remote_bot.id != bot.id or not remote_bot.bot:
            raise ValueError('MTProto identity differs from the verified Codex Bot.')
        from telethon import types
        peer = await transport.get_input_entity(types.PeerChannel(4440313456))
        if matching and previous.get('messageId'):
            message = await transport.get_messages(peer, ids=previous['messageId'])
            receipt = previous
        else:
            message = await transport.send_file(
                peer, str(path), force_document=True, file_size=size, parse_mode=None,
                caption=f'Database backup: {path.name}\nSHA-256: {digest}',
            )
            if message.document.size != size:
                raise ValueError('Telegram receipt size differs from the uploaded artifact.')
            receipt = {'chatId': LOG_CHAT_ID, 'messageId': message.id, 'filename': path.name,
                       'sizeBytes': size, 'sha256': digest, 'verified': False}
            # Save confirmed upload before the download so retries do not resend it.
            save_receipt(receipt_path, receipt)
        await transport.download_media(message, file=str(restore))
        if checksum(restore) != digest:
            raise ValueError('Downloaded backup hash differs from the source.')
        if path.suffix == '.sqlite3':
            with closing(sqlite3.connect(restore.resolve().as_uri() + '?mode=ro', uri=True)) as database:
                if database.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                    raise ValueError('Downloaded database failed restore validation.')
        receipt['verified'] = True
        save_receipt(receipt_path, receipt)
        return receipt
    finally:
        restore.unlink(missing_ok=True)
        await transport.disconnect()


async def execute(path: Path, receipt: Path, source: Path | None = None) -> dict:
    if source is not None and not path.exists():
        snapshot_sqlite(source, path)
    from telegram import Bot
    from telethon import TelegramClient
    identity = BackupIdentity(os.environ['BACKUP_BOT_TOKEN'], int(os.environ['TELEGRAM_API_ID']), os.environ['TELEGRAM_API_HASH'])
    transport = TelegramClient(None, identity.api_id, identity.api_hash, receive_updates=False)
    async with Bot(identity.token) as api:
        return await deliver(path, identity, receipt, api=api, transport=transport)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Verify and send a database backup to Codex Logs.')
    parser.add_argument('artifact', type=Path)
    parser.add_argument('receipt', type=Path)
    parser.add_argument('--source', type=Path, help='Create a consistent SQLite snapshot before delivery.')
    args = parser.parse_args(argv)
    try:
        result = asyncio.run(execute(args.artifact, args.receipt, args.source))
    except Exception as exc:
        # Third-party exception strings can contain credentials or request URLs.
        print(f'Backup failed: {type(exc).__name__}', file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
