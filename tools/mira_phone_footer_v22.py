#!/usr/bin/env python3
"""MIRA V22: konservativere Rufnummernschrift nach dem Displaytest."""
from pathlib import Path
from datetime import datetime
import ast
import fcntl
import hashlib
import json
import shutil
import subprocess
import sys
import time
HOME=Path.home()
SCRIPTS=HOME/'.kodi/userdata/scripts'
ROOT=HOME/'.cache/mira-phone'
STOP=ROOT/'popup-v11.stop'
BACKUPS=HOME/'.kodi/userdata/mira-backups'
LATEST=BACKUPS/'phone-footer-v22-latest'

def patch_calls(source):
    if '# MIRA_PHONE_FOOTER_V22' in source:raise RuntimeError('V22 ist bereits installiert.')
    if '# MIRA_PHONE_FOOTER_V21' not in source:raise RuntimeError('Bitte zuerst V21 installieren.')
    old='    number_size=38 if number_length<=13 else 34 if number_length<=14 else 32 if number_length<=15 else 30'
    new='    number_size=38 if number_length<=11 else 34 if number_length<=12 else 32 if number_length<=13 else 30'
    if source.count(old)!=1:raise RuntimeError('Rufnummern-Schriftstaffel hat einen unbekannten Stand; nichts geändert.')
    source='# MIRA_PHONE_FOOTER_V22\n'+source.replace(old,new,1)
    ast.parse(source);return source

def quiet():
    result=subprocess.run(['/usr/bin/python3',str(SCRIPTS/'mira_phone_call_backend.py')],input='{"action":"status"}',capture_output=True,text=True,timeout=25)
    try:status=json.loads(result.stdout)
    except ValueError:status={}
    if not status.get('ok'):raise RuntimeError('Anrufstatus konnte nicht sicher geprüft werden; nichts geändert.')
    if status.get('calls'):raise RuntimeError('Bitte laufenden Anruf oder Simulation zuerst beenden.')
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700);STOP.write_text('stop')
    lock=None
    try:
        subprocess.run(['kodi-send','--action=Dialog.Close(1190)'],capture_output=True,check=False)
        subprocess.run(['kodi-send','--action=ActivateWindow(Home)'],capture_output=True,check=True)
        lock=(ROOT/'call-watch.lock').open('a');deadline=time.monotonic()+35
        while True:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);return lock
            except BlockingIOError:
                if time.monotonic()>=deadline:raise RuntimeError('Anrufbeobachter konnte nicht angehalten werden. Keine Dateien geändert.')
                time.sleep(0.2)
    except Exception:
        if lock is not None:lock.close()
        STOP.unlink(missing_ok=True);raise

def start():subprocess.run(['kodi-send','--action=RunScript(%s)'%(SCRIPTS/'mira_phone_call_watch.py')],check=False)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def reload():subprocess.run(['kodi-send','--action=ReloadSkin()'],check=False)

def install():
    calls_path=SCRIPTS/'mira_phone_calls.py'
    changes={calls_path:patch_calls(calls_path.read_text()).encode()}
    folder=BACKUPS/('phone-footer-v22-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir(parents=True,mode=0o700);records=[]
    for i,(path,data) in enumerate(changes.items()):
        before=digest(path);saved=str(i)+'.bak'
        if before is not None:shutil.copy2(path,folder/saved)
        records.append(dict(path=str(path),before=before,backup=saved,after=hashlib.sha256(data).hexdigest()))
    (folder/'manifest.json').write_text(json.dumps(records,indent=2))
    lock=quiet()
    try:
        try:
            for path,data in changes.items():
                path.parent.mkdir(parents=True,exist_ok=True)
                temp=path.with_suffix('.v22.tmp');temp.write_bytes(data);temp.replace(path)
        except Exception:
            for item in records:
                path=Path(item['path'])
                if item['before'] is None:path.unlink(missing_ok=True)
                else:shutil.copy2(folder/item['backup'],path)
            raise
    finally:
        lock.close();STOP.unlink(missing_ok=True);start()
    LATEST.unlink(missing_ok=True);LATEST.symlink_to(folder.name)
    reload();print('V22 installiert: Rufnummern wählen eine kleinere, zur verfügbaren Breite passende Schriftstufe.')
    print('Backup: '+str(folder));print('Keine Anrufe gestartet oder verändert. Uhrzeit, Empfang und Akku bleiben an ihrem Platz.')

def rollback():
    folder=LATEST.resolve(strict=True);records=json.loads((folder/'manifest.json').read_text())
    for item in records:
        if digest(Path(item['path']))!=item['after']:raise RuntimeError('Datei inzwischen geändert: '+item['path'])
    lock=quiet()
    try:
        for item in records:
            path=Path(item['path'])
            if item['before'] is None:path.unlink(missing_ok=True)
            else:shutil.copy2(folder/item['backup'],path)
    finally:
        lock.close();STOP.unlink(missing_ok=True);start()
    reload();print('V22 zurückgenommen; vorheriger Footer wieder aktiv.')

def backup_git():
    repo=HOME/'rpi-automotive-setup'
    def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True)
    if git('branch','--show-current').stdout.strip()!='main':raise RuntimeError('Nicht auf main.')
    git('fetch','origin');git('merge-base','--is-ancestor','origin/main','HEAD')
    mappings=[(SCRIPTS/'mira_phone_calls.py','mira/userdata/scripts/mira_phone_calls.py'),
              (Path(__file__).resolve(),'tools/mira_phone_footer_v22.py')]
    paths=[r for s,r in mappings];status=git('status','--porcelain','--',*paths).stdout
    if status.strip():raise RuntimeError('Exportziele haben lokale Änderungen:\n'+status)
    for source,relative in mappings:
        target=repo/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    git('add','--',*paths)
    result=subprocess.run(['git','-C',str(repo),'diff','--cached','--quiet','--',*paths])
    if result.returncode==1:print(git('commit','--only','-m','MIRA: Rufnummernschrift im Footer nach Praxistest angepasst','--',*paths).stdout)
    elif result.returncode:raise RuntimeError('Git-Diff fehlgeschlagen.')
    result=git('push','origin','main');print(result.stdout+result.stderr);print('GitHub-Sicherung abgeschlossen.')

if __name__=='__main__':
    try:
        if len(sys.argv)==1:install()
        elif sys.argv[1:]==['--rollback']:rollback()
        elif sys.argv[1:]==['--backup-git']:backup_git()
        else:raise RuntimeError('Optionen: --rollback oder --backup-git')
    except Exception as error:raise SystemExit('Abgebrochen: '+str(error))
