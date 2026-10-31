#!/usr/bin/env python3
"""MIRA V27: mehr Namensbreite und Laufschrift nur bei aktiver Auswahl."""
from pathlib import Path
from datetime import datetime
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
LATEST=BACKUPS/'phone-lists-v27-latest'

MARKER='MIRA_PHONE_LISTS_V27'

def put(node,key,value):
    child=node.find(key)
    if child is None:child=ET.SubElement(node,key)
    child.text=str(value)
    return child

def patch_phone(source):
    if MARKER.encode() in source:raise RuntimeError('V27 ist bereits installiert.')
    root=ET.fromstring(source,parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    if root.get('id')!='1189':raise RuntimeError('Unerwartetes Telefonfenster.')
    listing=root.find(".//control[@id='50']")
    if listing is None or listing.findtext('width')!='870' or listing.findtext('height')!='750':raise RuntimeError('Erwartete Telefonliste fehlt.')
    for tag in ('itemlayout','focusedlayout'):
        layout=listing.find(tag)
        if layout is None or layout.get('height')!='150':raise RuntimeError('Unbekanntes Listenlayout.')
        names=layout.findall(".//control[@type='group'][left='120'][width='425']")
        times=layout.findall(".//control[@type='group'][left='565'][width='285']")
        if len(names)!=1 or len(times)!=1:raise RuntimeError('Bitte zuerst V26 installieren; Namens- und Zeitspalte nicht eindeutig.')
        put(names[0],'width',475)
        labels=names[0].findall("control[@type='label']")
        if len(labels)!=2 or any(n.findtext('width')!='425' for n in labels):raise RuntimeError('Abweichende Namensbeschriftungen.')
        for label in labels:put(label,'width',475)
        put(times[0],'left',615);put(times[0],'width',235)
        labels=times[0].findall("control[@type='label']")
        if len(labels)!=2 or any(n.findtext('width')!='285' for n in labels):raise RuntimeError('Abweichende Zeitbeschriftungen.')
        for label in labels:put(label,'width',235)
        # Kodi's focused layout also represents the selected item when focus is elsewhere.
        # Give that case a static counterpart so only the actively selected row scrolls.
        parents={child:parent for parent in layout.iter() for child in parent}
        primary=[n for n in layout.iter('control') if n.get('type')=='label'
                 and n.findtext('font')=='MiraPhoneListNameV25'
                 and n.findtext('label')=='$INFO[ListItem.Label]']
        if len(primary)!=2:raise RuntimeError('Kontakt- und Anrufnamen sind nicht eindeutig.')
        for label in primary:
            if tag=='itemlayout':put(label,'scroll','false');continue
            static=copy.deepcopy(label);base=label.findtext('visible','').strip()
            put(label,'scroll','true')
            put(label,'visible',(base+' + ' if base else '')+'Control.HasFocus(50)')
            put(static,'scroll','false')
            put(static,'visible',(base+' + ' if base else '')+'!Control.HasFocus(50)')
            parent=parents[label];parent.insert(list(parent).index(label)+1,static)
    root.append(ET.Comment(MARKER));ET.indent(root,space='    ')
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
    phone_path=SKIN/'custom_MiraPhone.xml'
    changes={phone_path:patch_phone(phone_path.read_bytes())}
    folder=BACKUPS/('phone-lists-v27-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
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
                temp=path.with_suffix('.v27.tmp');temp.write_bytes(data);temp.replace(path)
        except Exception:
            for item in records:
                path=Path(item['path'])
                if item['before'] is None:path.unlink(missing_ok=True)
                else:shutil.copy2(folder/item['backup'],path)
            raise
    finally:
        lock.close();STOP.unlink(missing_ok=True);start()
    LATEST.unlink(missing_ok=True);LATEST.symlink_to(folder.name)
    reload();print('V27 installiert: breitere Namensspalte und Laufschrift nur bei angewählter Zeile mit Listenfokus.')
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
    reload();print('V27 zurückgenommen; vorherige Listenansicht wieder aktiv.')

def backup_git():
    repo=HOME/'rpi-automotive-setup'
    def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True)
    if git('branch','--show-current').stdout.strip()!='main':raise RuntimeError('Nicht auf main.')
    git('fetch','origin');git('merge-base','--is-ancestor','origin/main','HEAD')
    mappings=[(SKIN/'custom_MiraPhone.xml','mira/skin.estuary.custom/xml/custom_MiraPhone.xml'),
              (Path(__file__).resolve(),'tools/mira_phone_lists_v27.py')]
    paths=[r for s,r in mappings];status=git('status','--porcelain','--',*paths).stdout
    if status.strip():raise RuntimeError('Exportziele haben lokale Änderungen:\n'+status)
    for source,relative in mappings:
        target=repo/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    git('add','--',*paths)
    result=subprocess.run(['git','-C',str(repo),'diff','--cached','--quiet','--',*paths])
    if result.returncode==1:print(git('commit','--only','-m','MIRA: Mehr Namensbreite und Laufschrift bei Listenauswahl','--',*paths).stdout)
    elif result.returncode:raise RuntimeError('Git-Diff fehlgeschlagen.')
    result=git('push','origin','main');print(result.stdout+result.stderr);print('GitHub-Sicherung abgeschlossen.')

if __name__=='__main__':
    try:
        if len(sys.argv)==1:install()
        elif sys.argv[1:]==['--rollback']:rollback()
        elif sys.argv[1:]==['--backup-git']:backup_git()
        else:raise RuntimeError('Optionen: --rollback oder --backup-git')
    except Exception as error:raise SystemExit('Abgebrochen: '+str(error))
