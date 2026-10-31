#!/usr/bin/env python3
"""MIRA V20: kraeftige Aufbaupunkte im Timerbereich der Anruf-Pill."""
from pathlib import Path
from datetime import datetime
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
HOME=Path.home()
SKIN=HOME/'.kodi/addons/skin.estuary.custom/xml'
BACKUPS=HOME/'.kodi/userdata/mira-backups'
LATEST=BACKUPS/'phone-footer-v20-latest'
ASSETS={'mira/phone-footer-v20-dialing.png': 'iVBORw0KGgoAAAANSUhEUgAAAIoAAABKCAYAAABkb8zQAAACJklEQVR4nO3aT4oTQRiG8a8SwZWgCO6clQsX3sGFiMcQPMHcwNzDEwiewI1u3YngQnSrDIg7IWgmeVx0lSmCTjox6Wr1+UEzk6ar+v2g+k9VEiFJkiRJkiRJkiRJkiRJkiRJkiRJkqR/XBrqRMDPc6WUGOq8uzJnA0ACLtVF5f1TYNIq1yZzNgRMNz5fA67W+zePacGcDZXRDdwAZsAr4Eve3gJPgDv5mMEef+YckaqoB8BHfu87cJpvp4NfCeZsqAQE7lcFLIAlsMrbstoHMKvbmvPvy7mTPJITcB04y0WcX3AFrPJVsALu5j6OXpw5G6tG/6wa+duUwl8AEwZ4czdnY6ynbq/ZPvqLcvucAye5n6MWZ879HKQTIOVFnysRcRLdQl6fvlNEEBGXI+JWte8ozLm/Q18VfQs6VLt9mXNHB+kspQTd/H0eEZ+jG9V9l5VTRCwi4lP+fLTlaHPu75CjbpJSmkfEy+jCrnq0Kcd8iIj3+Zbbp92fMGdLrBeGbucXr0V+sbrIt/z3YW47xLTTnK2xntKd5sDneasLLItEpahndFO5FgtZ5myluhIeb4z2JevVw+Ip3ZdbiYG/ozDnCJSQwD3gOfC1KmYBvAEebR5vzvHmPOZawDSltMz/34z1vP4sIt6llFaloJY/vDHnCND9oOaXg5ERPUPNud0gt9L8nC3nIiIY46g3pyRJkiRJkiRJkiRJkiRJkiRJkiRJkv5jPwBOn0e6x1YAAwAAAABJRU5ErkJggg=='}

def put(node,key,value):
    child=node.find(key)
    if child is None:child=ET.SubElement(node,key)
    child.text=str(value)
    return child

def patch_footer(source):
    root=ET.fromstring(source)
    includes=root.findall(".//include[@name='RNSE_GlobalFooter']")
    if root.tag=='include' and root.get('name')=='RNSE_GlobalFooter':includes=[root]
    if len(includes)!=1:raise RuntimeError('Gemeinsamer Footer nicht eindeutig.')
    footer=includes[0]
    held=[n for n in footer.iter('control') if n.findtext('texture')=='mira/phone-footer-v19-held.png']
    if len(held)!=1:raise RuntimeError('Bitte zuerst V19 installieren; nichts geändert.')
    parents={child:parent for parent in footer.iter() for child in parent}
    pill=parents[held[0]]
    nodes=[n for n in pill.findall("control[@type='label']") if n.findtext('label')=='[B]…[/B]']
    if len(nodes)!=1:raise RuntimeError('Aufbauanzeige hat einen unbekannten Stand.')
    node=nodes[0]
    if (node.findtext('left'),node.findtext('width'),node.findtext('height'))!=('362','138','74'):
        raise RuntimeError('Aufbauanzeige hat eine abweichende Geometrie.')
    node.set('type','image')
    for key in ('font','textcolor','align','aligny','scroll','label'):
        for child in node.findall(key):node.remove(child)
    put(node,'texture','mira/phone-footer-v20-dialing.png')
    ET.indent(root,space='    ')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def reload():subprocess.run(['kodi-send','--action=ReloadSkin()'],check=False)

def install():
    include_path=SKIN/'Includes_RNSE_AppShell.xml'
    changes={include_path:patch_footer(include_path.read_bytes())}
    for relative,encoded in ASSETS.items():
        path=SKIN.parent/'media'/relative
        if path.exists():raise RuntimeError('Neue Buttontextur existiert bereits: '+str(path))
        data=base64.b64decode(encoded,validate=True)
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise RuntimeError('Ungültige Grafik.')
        changes[path]=data
    folder=BACKUPS/('phone-footer-v20-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir(parents=True,mode=0o700);records=[]
    for i,(path,data) in enumerate(changes.items()):
        before=digest(path);saved=str(i)+'.bak'
        if before is not None:shutil.copy2(path,folder/saved)
        records.append(dict(path=str(path),before=before,backup=saved,after=hashlib.sha256(data).hexdigest()))
    (folder/'manifest.json').write_text(json.dumps(records,indent=2))
    try:
        for path,data in changes.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            temp=path.with_suffix('.v20.tmp');temp.write_bytes(data);temp.replace(path)
    except Exception:
        for item in records:
            path=Path(item['path'])
            if item['before'] is None:path.unlink(missing_ok=True)
            else:shutil.copy2(folder/item['backup'],path)
        raise
    LATEST.unlink(missing_ok=True);LATEST.symlink_to(folder.name)
    reload();print('V20 installiert: kräftige Aufbaupunkte passend zur Halteanzeige.')
    print('Backup: '+str(folder));print('Keine Anrufe gestartet oder verändert. Uhrzeit, Empfang und Akku bleiben an ihrem Platz.')

def rollback():
    folder=LATEST.resolve(strict=True);records=json.loads((folder/'manifest.json').read_text())
    for item in records:
        if digest(Path(item['path']))!=item['after']:raise RuntimeError('Datei inzwischen geändert: '+item['path'])
    for item in records:
        path=Path(item['path'])
        if item['before'] is None:path.unlink(missing_ok=True)
        else:shutil.copy2(folder/item['backup'],path)
    reload();print('V20 zurückgenommen; vorheriger Footer wieder aktiv.')

def backup_git():
    repo=HOME/'rpi-automotive-setup'
    def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True)
    if git('branch','--show-current').stdout.strip()!='main':raise RuntimeError('Nicht auf main.')
    git('fetch','origin');git('merge-base','--is-ancestor','origin/main','HEAD')
    mappings=[(SKIN/'Includes_RNSE_AppShell.xml','mira/skin.estuary.custom/xml/Includes_RNSE_AppShell.xml')]
    mappings += [(SKIN.parent/'media'/relative,'mira/skin.estuary.custom/media/'+relative) for relative in ASSETS]
    mappings += [(Path(__file__).resolve(),'tools/mira_phone_footer_v20.py')]
    paths=[r for s,r in mappings];status=git('status','--porcelain','--',*paths).stdout
    if status.strip():raise RuntimeError('Exportziele haben lokale Änderungen:\n'+status)
    for source,relative in mappings:
        target=repo/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    git('add','--',*paths)
    result=subprocess.run(['git','-C',str(repo),'diff','--cached','--quiet','--',*paths])
    if result.returncode==1:print(git('commit','--only','-m','MIRA: Einheitliche Punkte fuer den Anrufaufbau','--',*paths).stdout)
    elif result.returncode:raise RuntimeError('Git-Diff fehlgeschlagen.')
    result=git('push','origin','main');print(result.stdout+result.stderr);print('GitHub-Sicherung abgeschlossen.')

if __name__=='__main__':
    try:
        if len(sys.argv)==1:install()
        elif sys.argv[1:]==['--rollback']:rollback()
        elif sys.argv[1:]==['--backup-git']:backup_git()
        else:raise RuntimeError('Optionen: --rollback oder --backup-git')
    except Exception as error:raise SystemExit('Abgebrochen: '+str(error))
