from pathlib import Path
import contextlib
import io
import json
import runpy
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts import vps_operations as ops
from scripts.vps_transport import VpsTransport
from scripts.frontend_release import FrontendRelease
from deploy.vps import patch_config as credentials


class VpsDeployTests(unittest.TestCase):
    def test_strict_key_transport_and_error_redaction(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            key=root/'private-key'; key.touch()
            hosts=root/'known-hosts'; hosts.touch()
            config=root/'config.json'
            values={'host':'207.180.234.227','user':'root','identityFile':str(key),'knownHostsFile':str(hosts)}
            config.write_text(json.dumps(values))
            run=Mock(return_value=SimpleNamespace(returncode=0,stdout=' result\n'))
            transport=VpsTransport(config,run=run)
            self.assertEqual(transport.remote('id -u'),'result')
            transport.upload(key,'/opt/galerazo/image.tar')
            transport.download('/opt/galerazo/media.bin',key)
            for call in run.call_args_list:
                self.assertIn('StrictHostKeyChecking=yes',call.args[0])
                self.assertIn('BatchMode=yes',call.args[0])
                self.assertFalse(call.kwargs.get('shell',False))
            run.return_value=SimpleNamespace(returncode=1,stdout='SECRET',stderr='SECRET')
            with self.assertRaisesRegex(RuntimeError,'private output withheld') as error:
                transport.remote('false')
            self.assertNotIn('SECRET',str(error.exception))
            for field,bad in [('host','bad;command'),('user','-root')]:
                config.write_text(json.dumps({**values,field:bad}))
                with self.assertRaises(ValueError): VpsTransport(config)
            for field in ('identityFile','knownHostsFile'):
                config.write_text(json.dumps({**values,field:str(root/'missing')}))
                with self.assertRaises(FileNotFoundError): VpsTransport(config)

    def test_publish_validates_builds_transfers_and_records_only_confirmed_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            transport=Mock(); transport.invoke.side_effect=lambda args: '' if 'status' in args else 'abcdef123456'
            run=Mock(return_value=SimpleNamespace(returncode=0))
            self.assertEqual(ops.operate(root,transport,'publish',run=run),'galerazo-bot:abcdef123456')
            self.assertEqual((root/'deploy/out/last-image.txt').read_text(),'galerazo-bot:abcdef123456\n')
            self.assertEqual(len(run.call_args_list),3)
            self.assertIn('check_release_broadcast.py',run.call_args_list[1].args[0][1])
            self.assertIn('docker load',transport.remote.call_args_list[0].args[0])
            self.assertIn('rm -f --',transport.remote.call_args_list[-1].args[0])
            ops.operate(root,transport,'publish',tag='explicit-tag',run=run)
            for outcomes in ([1],[0,1],[0,0,1]):
                run.side_effect=[SimpleNamespace(returncode=value) for value in outcomes]
                with self.assertRaises(RuntimeError): ops.operate(root,transport,'publish',run=run)
            run.side_effect=None
            with self.assertRaises(ValueError): ops.operate(root,transport,'publish',tag='bad;tag',run=run)
            transport.upload.side_effect=OSError('upload failed')
            with self.assertRaises(OSError): ops.operate(root,transport,'publish',run=run)
            self.assertIn('rm -f --',transport.remote.call_args.args[0])
            transport.invoke.side_effect=lambda args:'dirty'
            with self.assertRaisesRegex(RuntimeError,'committed and clean'):ops.operate(root,transport,'publish',run=run)

    def test_deploy_rollback_botctl_and_private_patch_use_fixed_commands(self):
        transport=Mock();transport.remote.return_value='{}'
        ops.operate('.',transport,'deploy',image='galerazo-bot:abc')
        self.assertEqual(transport.upload.call_count,4)
        self.assertIn('deploy.sh galerazo-bot:abc',transport.remote.call_args.args[0])
        for image in (None,'registry.invalid/image:tag','galerazo-bot:bad;sh'):
            with self.assertRaises(ValueError): ops.operate('.',transport,'deploy',image=image)
        ops.operate('.',transport,'rollback')
        self.assertEqual(transport.remote.call_args.args[0],'bash /opt/galerazo/rollback.sh')
        ops.operate('.',transport,'credential-status')
        self.assertEqual(transport.remote.call_args.args[0],'python3 /opt/galerazo/patch_config.py')
        ops.operate('.',transport,'credentials',patch='private.json')
        self.assertIn('rm -f -- /etc/galerazo/patch-',transport.remote.call_args.args[0])
        transport.upload.side_effect=OSError('private upload failed')
        with self.assertRaises(OSError): ops.operate('.',transport,'credentials',patch='private.json')
        self.assertIn('rm -f --',transport.remote.call_args.args[0])
        transport.upload.side_effect=None
        for action in ('status','triggers','stop','moderate','notify-release'):
            self.assertEqual(ops.operate('.',transport,action,arguments=('a; b',)),'{}')
            self.assertIn("'a; b'",transport.remote.call_args.args[0])
        ops.operate('.',transport,'media',arguments=('opaque',),output='media.bin')
        self.assertEqual(transport.download.call_args.args[1],'media.bin')
        self.assertIn('rm -f --',transport.remote.call_args.args[0])
        with self.assertRaises(ValueError): ops.operate('.',transport,'shell')

    def test_cli_and_frontend_probe_use_vps_without_gcloud(self):
        with patch.object(ops,'VpsTransport') as transport,patch.object(ops,'operate',return_value='ok') as operate,contextlib.redirect_stdout(io.StringIO()):
            ops.main(['--config','private.json','--action','status'])
            transport.assert_called_once_with('private.json')
            self.assertEqual(operate.call_args.args[2],'status')
        with patch.object(sys,'argv',['vps_operations','--help']),contextlib.redirect_stdout(io.StringIO()),self.assertRaises(SystemExit) as result:
            runpy.run_module('scripts.vps_operations',run_name='__main__')
        self.assertEqual(result.exception.code,0)
        with patch('scripts.frontend_release.VpsTransport') as transport:
            transport.return_value.remote.return_value='{"Running":true,"Health":{"Status":"healthy"}}\ngalerazo-bot:abc\n0.76'
            run=Mock()
            release=FrontendRelease('.','contabo','europe','vmi3680696',run=run,vps_config='private.json')
            self.assertEqual(release.backend(),('0.76','galerazo-bot:abc'))
            run.assert_not_called()


class CredentialPatchTests(unittest.TestCase):
    def test_preserves_unknown_settings_and_masks_presence(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'bot.env'
            path.write_text('# private\nTELEGRAM_BOT_TOKEN=original\nMINI_APP_PROXY_SECRET=preserve\nIGNORED\n')
            result=credentials.apply(path,{'updates':{'TELEGRAM_DEV_USER_IDS':' 123 '},'clear':['OPENAI_API_KEY']})
            self.assertTrue(result['TELEGRAM_BOT_TOKEN'])
            self.assertFalse(result['OPENAI_API_KEY'])
            self.assertIn('MINI_APP_PROXY_SECRET=preserve',path.read_text())
            self.assertIn('TELEGRAM_DEV_USER_IDS=123',path.read_text())
            account={'type':'service_account','client_email':'fixture@example.invalid','private_key':'fixture'}
            with patch.object(credentials.os,'chown',create=True) as ownership:
                result=credentials.apply(path,{'updates':{'GOOGLE_SHEETS_CREDENTIALS_JSON':account}})
                ownership.assert_called_once()
            self.assertTrue(result['GOOGLE_SHEETS_CREDENTIALS_JSON'])
            self.assertEqual(json.loads(path.with_name('google-sheets.json').read_text()),account)
            self.assertFalse(credentials.apply(path,{'clear':['GOOGLE_SHEETS_CREDENTIALS_JSON']})['GOOGLE_SHEETS_CREDENTIALS_JSON'])

    def test_rejects_invalid_values_without_replacing_main_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'bot.env'; path.write_text('TELEGRAM_BOT_TOKEN=original\n')
            bad=[{}, {'updates':[]},{'clear':{}},{'clear':['TELEGRAM_BOT_TOKEN']},
                 {'updates':{'UNEXPECTED':'x'}},{'updates':{'OPENAI_API_KEY':'x'},'clear':['OPENAI_API_KEY']},
                 *({'updates':{'OPENAI_API_KEY':value}} for value in ('',5,'a\nb','a\rb','a\0b')),
                 *({'updates':{'GOOGLE_SHEETS_CREDENTIALS_JSON':value}} for value in ('bad',{}, {'type':'x','client_email':'x','private_key':5}))]
            for value in bad:
                with self.subTest(value=value),self.assertRaises(ValueError): credentials.apply(path,value)
                self.assertEqual(path.read_text(),'TELEGRAM_BOT_TOKEN=original\n')
            path.write_text('OPENAI_API_KEY=x\n')
            with self.assertRaises(ValueError):credentials.apply(path,{'clear':['OPENAI_API_KEY']})

    def test_root_cli_status_patch_and_entrypoint_help(self):
        with patch.object(credentials.os,'getuid',return_value=1000,create=True),self.assertRaises(PermissionError):credentials.main([])
        with patch.object(credentials.os,'getuid',return_value=0,create=True),patch.object(credentials,'status',return_value={'token':True}) as status,contextlib.redirect_stdout(io.StringIO()):
            credentials.main([])
            status.assert_called_once()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'patch.json';path.write_text('{"updates":{"OPENAI_API_KEY":"fixture"}}')
            with patch.object(credentials.os,'getuid',return_value=0,create=True),patch.object(credentials,'apply',return_value={}) as apply,contextlib.redirect_stdout(io.StringIO()):
                credentials.main(['--patch',str(path)])
                self.assertEqual(apply.call_args.args[1]['updates']['OPENAI_API_KEY'],'fixture')
        with patch.object(sys,'argv',['patch_config','--help']),contextlib.redirect_stdout(io.StringIO()),self.assertRaises(SystemExit):runpy.run_module('deploy.vps.patch_config',run_name='__main__')
