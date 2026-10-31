#!/usr/bin/env python3
"""MIRA V23: ausgefuellter Telefonhoerer auf dem Anrufen-Button."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
HOME=Path.home()
SKIN=HOME/'.kodi/addons/skin.estuary.custom/xml'
BACKUPS=HOME/'.kodi/userdata/mira-backups'
LATEST=BACKUPS/'phone-icon-v23-latest'

ICON='mira/phone-footer-v17-receiver.png'

def patch_phone(source):
    root=ET.fromstring(source)
    if root.tag!='window' or root.get('id')!='1189':raise RuntimeError('Unerwartetes Telefonfenster.')
    button=root.find(".//control[@id='9612']")
    if button is None or button.get('type')!='button':raise RuntimeError('Anrufen-Button fehlt.')
    images=[n for n in root.iter('control') if n.get('type')=='image'
            and n.findtext('texture')=='home/mmi_icons_v1/phone.png'
            and 'Control.HasFocus(9612)' in n.findtext('visible','')]
    if not 1<=len(images)<=2:raise RuntimeError('Anrufen-Symbole haben einen unbekannten Stand oder wurden bereits ersetzt; nichts geändert.')
    for image in images:
        # Enlarge around the existing centre to preserve its position beside the label.
        values={key:float(image.findtext(key,'')) for key in ('left','top','width','height')}
        if not (16<=values['width']<=120 and 16<=values['height']<=120):
            raise RuntimeError('Unerwartete Symbolgröße; nichts geändert.')
        for key,old_size in (('width',values['width']),('height',values['height'])):
            new_size=round(old_size*1.25)
            image.find(key).text=str(new_size)
            pos='left' if key=='width' else 'top'
            image.find(pos).text=format(values[pos]-(new_size-old_size)/2,'g')
        texture=image.find('texture');texture.text=ICON
        texture.set('colordiffuse','FFFFFFFF')
    ET.indent(root,space='    ')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def reload():subprocess.run(['kodi-send','--action=ReloadSkin()'],check=False)

def install():
    path=SKIN/'custom_MiraPhone.xml'
    icon=SKIN.parent/'media'/ICON
    if not icon.is_file():raise RuntimeError('Ausgefüllter Hörer aus V17 fehlt; nichts geändert.')
    changes={path:patch_phone(path.read_bytes())}
    folder=BACKUPS/('phone-icon-v23-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir(parents=True,mode=0o700);records=[]
    for i,(path,data) in enumerate(changes.items()):
        before=digest(path);saved=str(i)+'.bak'
        if before is not None:shutil.copy2(path,folder/saved)
        records.append(dict(path=str(path),before=before,backup=saved,after=hashlib.sha256(data).hexdigest()))
    (folder/'manifest.json').write_text(json.dumps(records,indent=2))
    try:
        for path,data in changes.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            temp=path.with_suffix('.v23.tmp');temp.write_bytes(data);temp.replace(path)
    except Exception:
        for item in records:
            path=Path(item['path'])
            if item['before'] is None:path.unlink(missing_ok=True)
            else:shutil.copy2(folder/item['backup'],path)
        raise
    LATEST.unlink(missing_ok=True);LATEST.symlink_to(folder.name)
    reload();print('V23 installiert: ausgefüllter, um 25 Prozent größerer Hörer auf dem Anrufen-Button.')
    print('Backup: '+str(folder));print('Keine Anrufe gestartet oder verändert. Uhrzeit, Empfang und Akku bleiben an ihrem Platz.')

def rollback():
    folder=LATEST.resolve(strict=True);records=json.loads((folder/'manifest.json').read_text())
    for item in records:
        if digest(Path(item['path']))!=item['after']:raise RuntimeError('Datei inzwischen geändert: '+item['path'])
    for item in records:
        path=Path(item['path'])
        if item['before'] is None:path.unlink(missing_ok=True)
        else:shutil.copy2(folder/item['backup'],path)
    reload();print('V23 zurückgenommen; vorheriger Hörer wieder aktiv.')

def backup_git():
    repo=HOME/'rpi-automotive-setup'
    def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True)
    if git('branch','--show-current').stdout.strip()!='main':raise RuntimeError('Nicht auf main.')
    git('fetch','origin');git('merge-base','--is-ancestor','origin/main','HEAD')
    mappings=[(SKIN/'custom_MiraPhone.xml','mira/skin.estuary.custom/xml/custom_MiraPhone.xml'),
              (SKIN.parent/'media'/ICON,'mira/skin.estuary.custom/media/'+ICON),
              (Path(__file__).resolve(),'tools/mira_phone_icon_v23.py')]
    paths=[r for s,r in mappings];status=git('status','--porcelain','--',*paths).stdout
    if status.strip():raise RuntimeError('Exportziele haben lokale Änderungen:\n'+status)
    for source,relative in mappings:
        target=repo/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    git('add','--',*paths)
    result=subprocess.run(['git','-C',str(repo),'diff','--cached','--quiet','--',*paths])
    if result.returncode==1:print(git('commit','--only','-m','MIRA: Ausgefuellter Hoerer auf dem Anrufen-Button','--',*paths).stdout)
    elif result.returncode:raise RuntimeError('Git-Diff fehlgeschlagen.')
    result=git('push','origin','main');print(result.stdout+result.stderr);print('GitHub-Sicherung abgeschlossen.')

if __name__=='__main__':
    try:
        if len(sys.argv)==1:install()
        elif sys.argv[1:]==['--rollback']:rollback()
        elif sys.argv[1:]==['--backup-git']:backup_git()
        else:raise RuntimeError('Optionen: --rollback oder --backup-git')
    except Exception as error:raise SystemExit('Abgebrochen: '+str(error))
