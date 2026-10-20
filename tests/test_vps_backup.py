from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from unittest.mock import patch
import contextlib
import io
import runpy
import sys

from galerazo_bot.telegram_backup import BackupIdentity, snapshot_sqlite, deliver
from galerazo_bot.telegram_backup import execute, main


class SnapshotTests(unittest.TestCase):
    def test_snapshot_preserves_committed_rows_and_live_wal(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'live.sqlite3'
            target = Path(directory) / 'snapshot.sqlite3'
            with closing(sqlite3.connect(source)) as db:
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('CREATE TABLE marker(value TEXT)')
                db.execute("INSERT INTO marker VALUES ('committed')")
                db.commit()
                snapshot_sqlite(source, target)
                with closing(sqlite3.connect(target)) as restored:
                    self.assertEqual(restored.execute('SELECT value FROM marker').fetchone(), ('committed',))
                    self.assertEqual(restored.execute('PRAGMA integrity_check').fetchone(), ('ok',))

    def test_snapshot_refuses_missing_source_and_existing_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory)/'source', Path(directory)/'target'
            with self.assertRaises(FileNotFoundError):
                snapshot_sqlite(source, target)
            source.touch()
            target.touch()
            with self.assertRaises(FileExistsError):
                snapshot_sqlite(source, target)

    def test_logically_corrupt_source_never_publishes_a_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory)/'source.sqlite3', Path(directory)/'target.sqlite3'
            with closing(sqlite3.connect(source)) as db:
                db.execute('CREATE TABLE bad(value INTEGER CHECK(value>0))')
                db.execute('PRAGMA ignore_check_constraints=ON')
                db.execute('INSERT INTO bad VALUES (-1)')
                db.commit()
            with self.assertRaises(ValueError):
                snapshot_sqlite(source,target)
            self.assertFalse(target.exists())
            self.assertFalse(target.with_suffix('.sqlite3.partial').exists())


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'galerazo-20261020.sqlite3'
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('CREATE TABLE marker(value INTEGER)')
            db.execute('INSERT INTO marker VALUES (42)')
            db.commit()
        self.receipt = self.root / 'receipt.json'
        self.identity = BackupIdentity('fixture-secret', 1234, 'fixture-hash')
        self.api = SimpleNamespace(
            get_me=AsyncMock(return_value=SimpleNamespace(id=9, username='codexgalerazobot', first_name='Codex Bot', is_bot=True)),
            get_chat=AsyncMock(return_value=SimpleNamespace(id=-1004440313456, title='Codex - Logs', type='supergroup')),
            get_chat_member=AsyncMock(return_value=SimpleNamespace(status='administrator')),
        )
        async def download(_message, *, file):
            Path(file).write_bytes(self.path.read_bytes())
        self.transport = SimpleNamespace(
            connect=AsyncMock(), sign_in=AsyncMock(return_value=SimpleNamespace(id=9, bot=True)),
            get_input_entity=AsyncMock(return_value='authorized-peer'),
            send_file=AsyncMock(return_value=SimpleNamespace(id=123, document=SimpleNamespace(size=self.path.stat().st_size))),
            get_messages=AsyncMock(return_value='previous-message'),
            download_media=AsyncMock(side_effect=download), disconnect=AsyncMock(),
        )

    async def send(self, **kwargs):
        return await deliver(self.path, self.identity, self.receipt, api=self.api, transport=self.transport, **kwargs)

    async def test_round_trip_restores_backup_and_records_receipt_without_secrets(self):
        result = await self.send()
        self.assertTrue(result['verified'])
        self.assertEqual(result['messageId'], 123)
        self.assertEqual(result['sha256'], hashlib.sha256(self.path.read_bytes()).hexdigest())
        saved = json.loads(self.receipt.read_text())
        self.assertEqual(saved, result)
        self.assertNotIn('fixture-secret', self.receipt.read_text())
        self.assertFalse(self.path.with_suffix('.restore').exists())
        self.transport.disconnect.assert_awaited_once()

    async def test_completed_receipt_prevents_duplicate_upload(self):
        await self.send()
        await self.send()
        self.transport.send_file.assert_awaited_once()

    async def test_retry_verifies_already_sent_document_without_uploading_twice(self):
        self.transport.download_media.side_effect = OSError('fixture network failure')
        with self.assertRaises(OSError):
            await self.send()
        self.assertFalse(json.loads(self.receipt.read_text())['verified'])
        self.transport.download_media.side_effect = lambda _message, *, file: Path(file).write_bytes(self.path.read_bytes())
        await self.send()
        self.transport.send_file.assert_awaited_once()
        self.transport.get_messages.assert_awaited_once()

    async def test_wrong_bot_chat_or_admin_never_uploads(self):
        for field, value in [('username','another_bot'), ('first_name','Other'), ('is_bot',False)]:
            with self.subTest(field=field):
                identity = self.api.get_me.return_value
                old = getattr(identity, field)
                setattr(identity, field, value)
                with self.assertRaises(ValueError):
                    await self.send()
                setattr(identity, field, old)
        for field, value in [('id',-100123), ('title','Wrong'), ('type','private')]:
            with self.subTest(field=field):
                chat = self.api.get_chat.return_value
                old = getattr(chat, field)
                setattr(chat, field, value)
                with self.assertRaises(ValueError):
                    await self.send()
                setattr(chat, field, old)
        self.api.get_chat_member.return_value.status = 'member'
        with self.assertRaises(ValueError):
            await self.send()
        self.transport.send_file.assert_not_awaited()

    async def test_wrong_mtproto_identity_disconnects_without_upload(self):
        for identity in [SimpleNamespace(id=10, bot=True), SimpleNamespace(id=9, bot=False)]:
            self.transport.sign_in.return_value = identity
            with self.assertRaises(ValueError):
                await self.send()
        self.transport.send_file.assert_not_awaited()
        self.assertEqual(self.transport.disconnect.await_count, 2)

    async def test_bad_size_or_corrupt_round_trip_never_marks_verified(self):
        self.transport.send_file.return_value.document.size = 1
        with self.assertRaises(ValueError):
            await self.send()
        self.transport.send_file.return_value.document.size = self.path.stat().st_size
        self.transport.download_media.side_effect = lambda _message, *, file: Path(file).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):
            await self.send()
        self.assertFalse(json.loads(self.receipt.read_text())['verified'])

    async def test_oversized_and_secret_files_are_rejected_before_network(self):
        with self.assertRaises(ValueError):
            await self.send(max_bytes=1)
        secret = self.root / '.env'
        secret.write_text('fixture')
        with self.assertRaises(ValueError):
            await deliver(secret,self.identity,self.receipt,api=self.api,transport=self.transport)
        self.api.get_me.assert_not_awaited()

    async def test_replaced_file_is_a_new_delivery_and_creator_is_valid(self):
        await self.send()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('INSERT INTO marker VALUES (43)')
            db.commit()
        self.api.get_chat_member.return_value.status = 'creator'
        await self.send()
        self.assertEqual(self.transport.send_file.await_count, 2)

    async def test_postgres_dump_round_trip_is_hash_verified(self):
        self.path = self.root / 'tivio.dump'
        self.path.write_bytes(b'PGDMP fixture archive')
        self.transport.send_file.return_value.document.size = self.path.stat().st_size
        self.assertTrue((await self.send())['verified'])

    async def test_matching_download_with_invalid_database_is_not_verified(self):
        # Corrupt the freelist count while retaining a readable SQLite header.
        data = bytearray(self.path.read_bytes())
        data[36:40] = (1).to_bytes(4, 'big')
        self.path.write_bytes(data)
        self.transport.send_file.return_value.document.size = self.path.stat().st_size
        with self.assertRaises(ValueError):
            await self.send()
        self.assertFalse(json.loads(self.receipt.read_text())['verified'])

    async def test_execute_builds_real_adapters_without_polling_and_snapshots_once(self):
        source = self.path
        self.path = self.root/'new.sqlite3'
        api_manager = AsyncMock()
        api_manager.__aenter__.return_value = self.api
        with patch.dict('os.environ',{'BACKUP_BOT_TOKEN':'fixture-secret','TELEGRAM_API_ID':'1234','TELEGRAM_API_HASH':'fixture-hash'}):
            with patch('telegram.Bot',return_value=api_manager), patch('telethon.TelegramClient',return_value=self.transport) as factory:
                result = await execute(self.path,self.receipt,source)
                self.assertTrue(result['verified'])
                await execute(self.path,self.receipt,source)
                await execute(self.path,self.receipt)
                factory.assert_called_with(None,1234,'fixture-hash',receive_updates=False)
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT value FROM marker').fetchone(),(42,))


class CommandLineTests(unittest.TestCase):
    def test_success_and_sanitized_failure(self):
        output, error = io.StringIO(),io.StringIO()
        with patch('galerazo_bot.telegram_backup.execute',new=AsyncMock(return_value={'verified':True})):
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(['fixture.sqlite3','receipt.json']),0)
        self.assertTrue(json.loads(output.getvalue())['verified'])
        with patch('galerazo_bot.telegram_backup.execute',new=AsyncMock(side_effect=RuntimeError('fixture-secret URL'))):
            with contextlib.redirect_stderr(error):
                self.assertEqual(main(['fixture.sqlite3','receipt.json']),1)
        self.assertIn('RuntimeError',error.getvalue())
        self.assertNotIn('fixture-secret',error.getvalue())

    def test_module_entry_point_help_is_offline(self):
        with patch.object(sys,'argv',['telegram_backup','--help']),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                runpy.run_module('galerazo_bot.telegram_backup',run_name='__main__')
        self.assertEqual(result.exception.code,0)
