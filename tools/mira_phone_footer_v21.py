#!/usr/bin/env python3
"""MIRA V21: zentrierte Anrufdaten, definierte Schriftgroessen und Statuszeichen."""
from pathlib import Path
from datetime import datetime
import ast
import base64
import copy
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
LATEST=BACKUPS/'phone-footer-v21-latest'
ASSETS={'mira/phone-footer-v21-held.png': 'iVBORw0KGgoAAAANSUhEUgAAAIoAAABKCAYAAABkb8zQAAABVklEQVR4nO3YQWoUQRQG4P+NUdcGcouQWwhCbplzeBE3IoSI20DQjZmXRc+A4kYn3T2p8ftgYHox7/1VVBU9lQAAAAAAAAAAAAAAAAAAAADA6urYAebS3auPpap6rlqj5x/CMSZ5zr4j5D+lE+Vdks7yY9r3uK+q7WxFX3j+oRdKd2+SbJLcJPmQZLt7XrRtpnn7kuQ6ybfksGN8pPzDLpTurqrq7j5P8jXJ2yPEeF9VH7v7VVU9/ssPR8t/tlaiBXWShyRvss7RnUw7v5L8nKHWEPlPYaEk06Drl+9r9pu73ovMfwoLpTLtxm3W25GPSV7vPs81RP6hF8ru792PJJ+TXK3YepPke5LbfZRDioyUf9iX2eS3F8KLJJdrtc000XdV9Wmf4aBCg+fnLx3romwu/92F227AS98//NF2rgu30fMDAAAAAAAAAAAAAAAAAAAAwEKeAB3Smcu+yszWAAAAAElFTkSuQmCC', 'mira/phone-footer-v21-dialing.png': 'iVBORw0KGgoAAAANSUhEUgAAAIoAAABKCAYAAABkb8zQAAABhUlEQVR4nO3YP0oDQRiG8Xey2AkiiK2NF9DC1iPYeQAh57H3BpZ6CA9hrYXgH7AU9bFwFlYxkuwqrPH5wRAmm7zFfjPLfpNIkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJkiRJ+mFAAcp/ydOCgAkw6cwL0Cxrnnr4VIA1YL0zX7gYY89TD20RgB3gDLgB7oAL4LBem7sYY89TD50i7AH3fG3a/e1fzlMP7UshsFF3KcAT8FrHcx0A+/U/M3fu2POSxJXUT1NKIclBks0kz0lWkpQ6miTUMV2CPBfKQNtJXmdca9vQrfrJX85zoQxzm9n3sN2xD3U+z/nFaPNcKP20u/Q87zd7ko87lzqfJDmt331XiLHnqa9OVzHtdBHdl0SAE6BZsEsZZZ4GaDsF4Ai46hTgETiu1+Y+Nh9zno+bgYCmlPICrCbZzXtHcVlKuW4LUDuQpcjTAF+dQQx5nI8xzyfKD6m7s735lFJmtaVLkSdJkiRJkiRJkiRJkiRJv+4NFDj6XKbha2MAAAAASUVORK5CYII='}

SIZES=(38,34,32,30)
NUMBER='String.IsEqual(Window(11189).Property(MiraPhoneFooterIsNumber),true)'

def number_size(number):
    length=len(str(number or '').strip())
    return 38 if length<=13 else 34 if length<=14 else 32 if length<=15 else 30

def put(node,key,value):
    child=node.find(key)
    if child is None:child=ET.SubElement(node,key)
    child.text=str(value)
    return child

def patch_fonts(source):
    root=ET.fromstring(source);sets=root.findall('fontset')
    if not sets:raise RuntimeError('Keine Schriftsets gefunden.')
    for fontset in sets:
        if any(n.findtext('name','').startswith('MiraPhoneFooterNumberV21_') for n in fontset.findall('font')):
            raise RuntimeError('V21-Schriften existieren bereits.')
        base=[n for n in fontset.findall('font') if n.findtext('name')=='font45']
        if len(base)!=1 or base[0].findtext('size')!='45' or not base[0].findtext('filename'):
            raise RuntimeError('font45 entspricht nicht der ausgelesenen Grundlage.')
        for size in SIZES:
            node=copy.deepcopy(base[0])
            put(node,'name','MiraPhoneFooterNumberV21_'+str(size))
            put(node,'size',size);put(node,'style','bold')
            fontset.append(node)
    ET.indent(root,space='    ')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def patch_calls(source):
    if 'MIRA_PHONE_FOOTER_V21' in source:raise RuntimeError('V21 ist bereits installiert.')
    if '# MIRA_PHONE_FOOTER_V19' not in source:raise RuntimeError('Bitte zuerst V19 installieren.')
    setter="    W.setProperty('MiraPhoneFooterIsNumber','true' if number and name==number else '')"
    if source.count(setter)!=1:raise RuntimeError('Rufnummern-Erkennung hat einen unbekannten Stand.')
    addition="    number_length=len(str(number or '').strip())\n    number_size=38 if number_length<=13 else 34 if number_length<=14 else 32 if number_length<=15 else 30\n    W.setProperty('MiraPhoneFooterNumberSize',str(number_size))"
    source='# MIRA_PHONE_FOOTER_V21\n'+source.replace(setter,setter+'\n'+addition,1)
    ast.parse(source);return source

def patch_footer(source):
    root=ET.fromstring(source)
    includes=root.findall(".//include[@name='RNSE_GlobalFooter']")
    if root.tag=='include' and root.get('name')=='RNSE_GlobalFooter':includes=[root]
    if len(includes)!=1:raise RuntimeError('Gemeinsamer Footer nicht eindeutig.')
    footer=includes[0]
    parents={child:parent for parent in footer.iter() for child in parent}
    held=[n for n in footer.iter('control') if n.findtext('texture')=='mira/phone-footer-v19-held.png']
    if len(held)!=1:raise RuntimeError('Bitte zuerst V19 und V20 installieren.')
    pill=parents[held[0]]
    dialing=[n for n in pill.findall('control') if n.findtext('texture')=='mira/phone-footer-v20-dialing.png']
    if len(dialing)!=1:raise RuntimeError('Bitte zuerst V20 installieren.')
    names=[n for n in pill.findall("control[@type='label']") if 'MiraPhoneCallName' in n.findtext('label','')]
    numbers=[n for n in pill.findall("control[@type='label']") if 'MiraPhoneCallNumber' in n.findtext('label','')]
    if len(names)!=1 or len(numbers)!=1 or numbers[0].findtext('visible')!=NUMBER:
        raise RuntimeError('Pill-Beschriftungen haben einen unbekannten Stand.')
    # The midpoint of this area matches the midpoint between receiver and timer.
    for node in (names[0],numbers[0]):
        for key,value in dict(left=64,width=292,align='center').items():put(node,key,value)
    old=numbers[0];index=list(pill).index(old);pill.remove(old)
    for offset,size in enumerate(SIZES):
        node=copy.deepcopy(old)
        put(node,'font','MiraPhoneFooterNumberV21_'+str(size))
        put(node,'visible',NUMBER+' + String.IsEqual(Window(11189).Property(MiraPhoneFooterNumberSize),'+str(size)+')')
        pill.insert(index+offset,node)
    held[0].find('texture').text='mira/phone-footer-v21-held.png'
    dialing[0].find('texture').text='mira/phone-footer-v21-dialing.png'
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
    fonts_path=SKIN/'Font.xml'
    changes={include_path:patch_footer(include_path.read_bytes()),
             calls_path:patch_calls(calls_path.read_text()).encode(),
             fonts_path:patch_fonts(fonts_path.read_bytes())}
    for relative,encoded in ASSETS.items():
        path=SKIN.parent/'media'/relative
        if path.exists():raise RuntimeError('Neue Buttontextur existiert bereits: '+str(path))
        data=base64.b64decode(encoded,validate=True)
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise RuntimeError('Ungültige Grafik.')
        changes[path]=data
    folder=BACKUPS/('phone-footer-v21-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
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
                temp=path.with_suffix('.v21.tmp');temp.write_bytes(data);temp.replace(path)
        except Exception:
            for item in records:
                path=Path(item['path'])
                if item['before'] is None:path.unlink(missing_ok=True)
                else:shutil.copy2(folder/item['backup'],path)
            raise
    finally:
        lock.close();STOP.unlink(missing_ok=True);start()
    LATEST.unlink(missing_ok=True);LATEST.symlink_to(folder.name)
    reload();print('V21 installiert: zentrierte Namen und Rufnummern, definierte Rufnummernschriften und abgestimmte Statuszeichen.')
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
    reload();print('V21 zurückgenommen; vorheriger Footer wieder aktiv.')

def backup_git():
    repo=HOME/'rpi-automotive-setup'
    def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True)
    if git('branch','--show-current').stdout.strip()!='main':raise RuntimeError('Nicht auf main.')
    git('fetch','origin');git('merge-base','--is-ancestor','origin/main','HEAD')
    mappings=[(SKIN/name,'mira/skin.estuary.custom/xml/'+name) for name in ('Includes_RNSE_AppShell.xml','Font.xml')]
    mappings += [(SCRIPTS/'mira_phone_calls.py','mira/userdata/scripts/mira_phone_calls.py')]
    mappings += [(SKIN.parent/'media'/relative,'mira/skin.estuary.custom/media/'+relative) for relative in ASSETS]
    mappings += [(Path(__file__).resolve(),'tools/mira_phone_footer_v21.py')]
    paths=[r for s,r in mappings];status=git('status','--porcelain','--',*paths).stdout
    if status.strip():raise RuntimeError('Exportziele haben lokale Änderungen:\n'+status)
    for source,relative in mappings:
        target=repo/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    git('add','--',*paths)
    result=subprocess.run(['git','-C',str(repo),'diff','--cached','--quiet','--',*paths])
    if result.returncode==1:print(git('commit','--only','-m','MIRA: Zentrierte Rufnummern und abgestimmte Statuszeichen im Footer','--',*paths).stdout)
    elif result.returncode:raise RuntimeError('Git-Diff fehlgeschlagen.')
    result=git('push','origin','main');print(result.stdout+result.stderr);print('GitHub-Sicherung abgeschlossen.')

if __name__=='__main__':
    try:
        if len(sys.argv)==1:install()
        elif sys.argv[1:]==['--rollback']:rollback()
        elif sys.argv[1:]==['--backup-git']:backup_git()
        else:raise RuntimeError('Optionen: --rollback oder --backup-git')
    except Exception as error:raise SystemExit('Abgebrochen: '+str(error))
