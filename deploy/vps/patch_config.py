"""Fixed, root-only credential patch used by Bot Control Center over SSH."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path

FIELDS = ('TELEGRAM_BOT_TOKEN','OPENAI_API_KEY','TELEGRAM_DEV_USER_IDS','TELEGRAM_LOG_CHAT_ID',
          'TELEGRAM_ANNOUNCEMENTS_CHAT_ID','GOOGLE_SHEETS_SPREADSHEET_ID',
          'GOOGLE_SHEETS_WORKSHEET_NAME','GOOGLE_SHEETS_CREDENTIALS_JSON')


def read_values(path):
    return dict(line.split('=',1) for line in path.read_text(encoding='utf-8').splitlines() if line and not line.startswith('#') and '=' in line)


def status(path):
    values=read_values(path)
    return {key:bool(values.get(key)) if key!='GOOGLE_SHEETS_CREDENTIALS_JSON' else bool(values.get('GOOGLE_SHEETS_CREDENTIALS_JSON_PATH')) for key in FIELDS}


def apply(path, patch):
    updates, clear=patch.get('updates',{}),patch.get('clear',[])
    if (not isinstance(updates,dict) or not isinstance(clear,list) or not (updates or clear)
        or (set(updates)|set(clear))-set(FIELDS) or set(updates)&set(clear) or 'TELEGRAM_BOT_TOKEN' in clear):
        raise ValueError('Invalid credential patch.')
    values=read_values(path)
    for key,value in updates.items():
        if key=='GOOGLE_SHEETS_CREDENTIALS_JSON':
            if not isinstance(value,dict) or not all(isinstance(value.get(k),str) and value[k] for k in ('type','client_email','private_key')):
                raise ValueError('Invalid service account.')
            account=path.with_name('google-sheets.json')
            atomic_write(account,json.dumps(value))
            os.chown(account,10001,10001)
            values['GOOGLE_SHEETS_CREDENTIALS_JSON_PATH']='/run/secrets/google-sheets.json'
        else:
            if not isinstance(value,str) or not value.strip() or any(c in value for c in '\r\n\0'):
                raise ValueError('Invalid credential value.')
            values[key]=value.strip()
    for key in clear:
        values['GOOGLE_SHEETS_CREDENTIALS_JSON_PATH' if key=='GOOGLE_SHEETS_CREDENTIALS_JSON' else key]=''
    if not values.get('TELEGRAM_BOT_TOKEN'):
        raise ValueError('Main token must remain configured.')
    atomic_write(path,''.join(f'{k}={v}\n' for k,v in values.items()))
    return status(path)


def atomic_write(path,text):
    temporary=path.with_suffix('.next')
    temporary.write_text(text,encoding='utf-8')
    os.chmod(temporary,0o600)
    temporary.replace(path)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--patch',type=Path)
    args=parser.parse_args(argv)
    if os.getuid()!=0:
        raise PermissionError('Root is required.')
    path=Path('/etc/galerazo/bot.env')
    result=apply(path,json.loads(args.patch.read_text(encoding='utf-8'))) if args.patch else status(path)
    print(json.dumps(result))


if __name__=='__main__':
    main()
