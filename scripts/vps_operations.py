"""Fixed deployment and botctl operations on the already contracted VPS."""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from scripts.vps_transport import VpsTransport


def operate(root, transport, action, *, image=None, tag=None, arguments=(), output=None, patch=None, run=subprocess.run):
    root=Path(root)
    if action=='publish':
        if transport.invoke(['git','-C',str(root),'status','--porcelain=v1','--untracked-files=normal']):
            raise RuntimeError('Release source must be committed and clean.')
        for script in ('runtime_versions.py','check_release_broadcast.py'):
            subprocess_result=run([sys.executable,str(root/'scripts'/script)],cwd=root,check=False)
            if subprocess_result.returncode:
                raise RuntimeError('Release validation failed.')
        tag=tag or transport.invoke(['git','-C',str(root),'rev-parse','--short=12','HEAD'])
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',tag):
            raise ValueError('Invalid image tag.')
        image='galerazo-bot:'+tag
        built=run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(root/'scripts/deploy/Build-DockerImage.ps1'),'-Tag',tag],cwd=root,check=False)
        if built.returncode:
            raise RuntimeError('Docker validation/build failed.')
        with tempfile.TemporaryDirectory(prefix='galerazo-image-') as temporary:
            archive=Path(temporary)/'image.tar'
            transport.invoke(['docker','save','--output',str(archive),image])
            remote='/opt/galerazo/image-'+uuid.uuid4().hex+'.tar'
            try:
                transport.upload(archive,remote)
                transport.remote('docker load --input '+remote)
            finally:
                transport.remote('rm -f -- '+remote)
        target=root/'deploy/out/last-image.txt'
        target.parent.mkdir(exist_ok=True,parents=True)
        target.write_text(image+'\n',encoding='ascii')
        return image
    if action=='deploy':
        if not image or not re.fullmatch(r'galerazo-bot:[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',image):
            raise ValueError('Invalid VPS image.')
        for source,name in [('compose.production.yaml','compose.base.yaml'),('compose.vps.yaml','compose.vps.yaml'),('deploy/vps/deploy.sh','deploy.sh'),('deploy/vps/rollback.sh','rollback.sh')]:
            transport.upload(root/source,'/opt/galerazo/'+name)
        transport.remote("cd /opt/galerazo && docker compose -f compose.base.yaml -f compose.vps.yaml config --no-interpolate --no-env-resolution > compose.next.yaml && mv compose.next.yaml compose.yaml && chmod 0755 deploy.sh rollback.sh")
        return transport.remote('bash /opt/galerazo/deploy.sh '+shlex.quote(image))
    if action=='rollback':
        return transport.remote('bash /opt/galerazo/rollback.sh')
    if action in {'credential-status','credentials'}:
        transport.upload(root/'deploy/vps/patch_config.py','/opt/galerazo/patch_config.py')
        if action=='credential-status':
            return transport.remote('python3 /opt/galerazo/patch_config.py')
        remote='/etc/galerazo/patch-'+uuid.uuid4().hex+'.json'
        try:
            transport.upload(Path(patch),remote)
            return transport.remote('chmod 0600 '+remote+' && python3 /opt/galerazo/patch_config.py --patch '+remote)
        finally:
            transport.remote('rm -f -- '+remote)
    if action not in {'status','triggers','media','moderate','stop','notify-release'}:
        raise ValueError('Unknown VPS action.')
    transport.upload(root/'deploy/vps/botctl.py','/opt/galerazo/botctl.py')
    remote_media='/opt/galerazo/media-'+uuid.uuid4().hex+'.bin'
    args=[action,*arguments]
    if action=='media':
        args.append(remote_media)
    try:
        result=transport.remote(shlex.join(['python3','/opt/galerazo/botctl.py',*args]))
        if action=='media':
            transport.download(remote_media,output)
        return result
    finally:
        if action=='media':
            transport.remote('rm -f -- '+remote_media)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--action',required=True)
    parser.add_argument('--image')
    parser.add_argument('--tag')
    parser.add_argument('--patch')
    parser.add_argument('--output')
    parser.add_argument('arguments',nargs='*')
    args=parser.parse_args(argv)
    result=operate(args.root,VpsTransport(args.config),args.action,image=args.image,tag=args.tag,arguments=args.arguments,output=args.output,patch=args.patch)
    print(result)


if __name__=='__main__':
    main()
