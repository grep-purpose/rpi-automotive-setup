#!/usr/bin/env python3
"""MIRA V19: verlässliche Rufnummernanzeige und kräftige Haltemarkierung."""
from pathlib import Path
from datetime import datetime
import ast
import base64
import fcntl
import hashlib
import json
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
HOME=Path.home()
SKIN=HOME/'.kodi/addons/skin.estuary.custom/xml'
SCRIPTS=HOME/'.kodi/userdata/scripts'
ROOT=HOME/'.cache/mira-phone'
STOP=ROOT/'popup-v11.stop'
BACKUPS=HOME/'.kodi/userdata/mira-backups'
LATEST=BACKUPS/'phone-footer-v19-latest'
ASSETS={'mira/phone-footer-v19-held.png': 'iVBORw0KGgoAAAANSUhEUgAAAIoAAABKCAYAAABkb8zQAAABaklEQVR4nO3ZTUpDMRSG4ffUv7GCuxB3IQju0nW4ESciiOJUEJ1oj4PeO3AiNwm2DXkf6OAO8vOF0/Q2AUmSJEmSJEmSJEmSJEmSJEmSJEmSJEmSForahplZ3XbXIiJb+xg9/yI9LxK0z3/E/C07yimQLX1s2TzXt4hYN3c2WP6ikJm5AlbALXANrKfnHswL9QjcAK9Qtg2PnH9xoWRmRERm5hnwApwUT3V/XEXEXWYeRMT3kgaj5z+sGCSBd+CYvrZe2OwAAXw19DFk/ppCgc12Oy9QTwsV/J57reHy9/L7qh2zULSIhaJFagtlOyd7/yNpn/9w+WteZoPNG/+a/t76v4Gj6VNryPxFhTId/X4CD8Bl6WB7YAV8AE/Tc9E3a+T8pSez86HTOXBR0nYPJJuFeo6I+zlLUQeD5x9O75d6rbZ2KTgN1Os/pmy9FBw9vyRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJf/oBM8Gf0+R9LeEAAAAASUVORK5CYII='}

NUMBER='String.IsEqual(Window(11189).Property(MiraPhoneFooterIsNumber),true)'

def put(node,key,value):
    child=node.find(key)
    if child is None:child=ET.SubElement(node,key)
    child.text=str(value)
    return child

def patch_calls(source):
    if 'MIRA_PHONE_FOOTER_V19' in source:raise RuntimeError('V19 ist bereits installiert.')
    tree=ast.parse(source)
    if len([n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='update'])!=1:
        raise RuntimeError('Anruf-Aktualisierung nicht eindeutig.')
    old="    if remote and number_key(remote)==number_key(number):remote=''"
    fixed="    if number_key(number) and remote and number_key(remote)==number_key(number):remote=''"
    if source.count(old)==1:source=source.replace(old,fixed,1)
    elif source.count(fixed)!=1:raise RuntimeError('Namensauflösung hat einen unbekannten Stand; nichts geändert.')
    setter="    W.setProperty('MiraPhoneCallName',name)"
    if source.count(setter)!=1:raise RuntimeError('Anrufername nicht eindeutig.')
    source=source.replace(setter,"    W.setProperty('MiraPhoneFooterIsNumber','true' if number and name==number else '')\n"+setter,1)
    source='# MIRA_PHONE_FOOTER_V19\n'+source
    ast.parse(source);return source

def patch_footer(source):
    root=ET.fromstring(source)
    includes=root.findall(".//include[@name='RNSE_GlobalFooter']")
    if root.tag=='include' and root.get('name')=='RNSE_GlobalFooter':includes=[root]
    if len(includes)!=1:raise RuntimeError('Gemeinsamer Footer nicht eindeutig.')
    footer=includes[0]
    parents={child:parent for parent in footer.iter() for child in parent}
    images=[n for n in footer.iter('control') if n.findtext('texture')=='mira/phone-footer-v18-normal.png']
    if len(images)!=1:raise RuntimeError('Erwarteter V18-Footer fehlt; nichts geändert.')
    pill=parents[images[0]]
    labels=pill.findall("control[@type='label']")
    names=[n for n in labels if 'MiraPhoneCallName' in n.findtext('label','')]
    numbers=[n for n in labels if 'MiraPhoneCallNumber' in n.findtext('label','')]
    held=[n for n in labels if n.findtext('label')=='[B]--[/B]']
    if len(labels)!=5 or len(names)!=1 or len(numbers)!=1 or len(held)!=1:
        raise RuntimeError('Pill-Beschriftungen haben einen unbekannten Stand.')
    # Kodi evaluates only a plain boolean property here, without nested $INFO comparisons.
    put(names[0],'visible','!'+NUMBER);put(numbers[0],'visible',NUMBER)
    node=held[0];node.set('type','image')
    for key in ('font','textcolor','align','aligny','scroll','label'):
        for element in node.findall(key):node.remove(element)
    put(node,'texture','mira/phone-footer-v19-held.png')
    ET.indent(root,space='    ')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

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
    include_path=SKIN/'Includes_RNSE_AppShell.xml'
    calls_path=SCRIPTS/'mira_phone_calls.py'
    changes={include_path:patch_footer(include_path.read_bytes()),
             calls_path:patch_calls(calls_path.read_text()).encode()}
    for relative,encoded in ASSETS.items():
        path=SKIN.parent/'media'/relative
        if path.exists():raise RuntimeError('Neue Buttontextur existiert bereits: '+str(path))
        data=base64.b64decode(encoded,validate=True)
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise RuntimeError('Ungültige Grafik.')
        changes[path]=data
    folder=BACKUPS/('phone-footer-v19-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
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
                temp=path.with_suffix('.v19.tmp');temp.write_bytes(data);temp.replace(path)
        except Exception:
            for item in records:
                path=Path(item['path'])
                if item['before'] is None:path.unlink(missing_ok=True)
                else:shutil.copy2(folder/item['backup'],path)
            raise
    finally:
        lock.close();STOP.unlink(missing_ok=True);start()
    LATEST.unlink(missing_ok=True);LATEST.symlink_to(folder.name)
    reload();print('V19 installiert: Name und Rufnummer im Footer korrigiert; Simulationsname erhalten; kräftige Halteanzeige.')
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
    reload();print('V19 zurückgenommen; vorheriger Footer wieder aktiv.')

def backup_git():
    repo=HOME/'rpi-automotive-setup'
    def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True)
    if git('branch','--show-current').stdout.strip()!='main':raise RuntimeError('Nicht auf main.')
    git('fetch','origin');git('merge-base','--is-ancestor','origin/main','HEAD')
    mappings=[(SKIN/'Includes_RNSE_AppShell.xml','mira/skin.estuary.custom/xml/Includes_RNSE_AppShell.xml'),
              (SCRIPTS/'mira_phone_calls.py','mira/userdata/scripts/mira_phone_calls.py')]
    mappings += [(SKIN.parent/'media'/relative,'mira/skin.estuary.custom/media/'+relative) for relative in ASSETS]
    mappings += [(Path(__file__).resolve(),'tools/mira_phone_footer_v19.py')]
    paths=[r for s,r in mappings];status=git('status','--porcelain','--',*paths).stdout
    if status.strip():raise RuntimeError('Exportziele haben lokale Änderungen:\n'+status)
    for source,relative in mappings:
        target=repo/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    git('add','--',*paths)
    result=subprocess.run(['git','-C',str(repo),'diff','--cached','--quiet','--',*paths])
    if result.returncode==1:print(git('commit','--only','-m','MIRA: Rufnummernanzeige im Footer und Simulationsname korrigiert','--',*paths).stdout)
    elif result.returncode:raise RuntimeError('Git-Diff fehlgeschlagen.')
    result=git('push','origin','main');print(result.stdout+result.stderr);print('GitHub-Sicherung abgeschlossen.')

if __name__=='__main__':
    try:
        if len(sys.argv)==1:install()
        elif sys.argv[1:]==['--rollback']:rollback()
        elif sys.argv[1:]==['--backup-git']:backup_git()
        else:raise RuntimeError('Optionen: --rollback oder --backup-git')
    except Exception as error:raise SystemExit('Abgebrochen: '+str(error))
