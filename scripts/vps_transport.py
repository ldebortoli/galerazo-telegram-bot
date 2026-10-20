"""Strict OpenSSH transport for the existing VPS; no passwords or cloud billing."""
from __future__ import annotations

import json
from pathlib import Path
import re
import shlex
import subprocess


class VpsTransport:
    def __init__(self, config, *, run=subprocess.run):
        values = json.loads(Path(config).read_text(encoding='utf-8'))
        self.host, self.user = values['host'], values['user']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]*', self.host) or not re.fullmatch(r'[a-z_][a-z0-9_-]*', self.user):
            raise ValueError('Invalid SSH host or user.')
        self.options = ['-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=yes',
                        '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=2']
        for field, option in (('identityFile', '-i'), ('knownHostsFile', '-o')):
            path = Path(values[field]).resolve()
            if not path.is_file():
                raise FileNotFoundError('SSH identity or known-hosts file is missing.')
            self.options.extend([option, str(path) if option == '-i' else 'UserKnownHostsFile=' + str(path)])
        self.target = self.user + '@' + self.host
        self.run = run

    def invoke(self, arguments):
        result = self.run(arguments, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=1800, check=False)
        if result.returncode:
            # Request errors can include private file contents or credential URLs.
            raise RuntimeError(f'{arguments[0]} failed (exit {result.returncode}); private output withheld.')
        return result.stdout.strip()

    def remote(self, command):
        return self.invoke(['ssh', *self.options, self.target, command])

    def upload(self, source, target):
        return self.invoke(['scp', *self.options, str(Path(source).resolve()), self.target + ':' + shlex.quote(target)])

    def download(self, source, target):
        return self.invoke(['scp', *self.options, self.target + ':' + shlex.quote(source), str(Path(target).resolve())])
