#!/usr/bin/env python3
"""MIRA V14: Telefonbuttons und Popup-Typografie bei unveränderter Transparenz polieren."""
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
LATEST=BACKUPS/'phone-buttons-v14-latest'
def patch_xml(source,expected):
    root=ET.fromstring(source)
    if root.get('id')!=('1189' if expected==4 else '1190'):raise RuntimeError('Unerwartete Fensterdefinition.')
    ids=(9612,9651,9652,9653) if expected==4 else (9660,9661)
    backgrounds=[ET.tostring(n) for n in root.iter('control') if n.get('type')=='image' and not n.findtext('texture','').startswith(('mira/phone-selected-v12-','mira/phone-selected-v13-'))]
    removed=0
    for parent in root.iter():
        for node in list(parent):
            if node.tag=='control' and node.get('type')=='image' and node.findtext('texture','').startswith(('mira/phone-selected-v12-','mira/phone-selected-v13-')):
                parent.remove(node);removed+=1
    if removed!=expected:raise RuntimeError('Erwarteter Fokusstand V12/V13 fehlt. Nichts geändert.')
    for cid in ids:
        node=root.find(".//control[@id='%d']"%cid)
        if node is None or node.get('type')!='button':raise RuntimeError('Anruf-Button fehlt: '+str(cid))
        texture=node.find('texturefocus')
        color=node.find('focusedcolor')
        if texture is None or color is None:raise RuntimeError('Fokusdefinition fehlt: '+str(cid))
        texture.set('colordiffuse','FFE4E8EC')
        color.text='FF10151C'
        font=node.find('font')
        if font is None:font=ET.SubElement(node,'font')
        font.text='font50'
        label=node.find('label')
        if label is not None and label.text:label.text=label.text.replace('[B]','').replace('[/B]','')
    if expected==2:
        labels=root.find('controls').findall("control[@type='label']")
        if len(labels)!=3 or labels[0].findtext('label')!='Eingehender Anruf':
            raise RuntimeError('Popup-Typografie hat einen unerwarteten Stand.')
        fields=(dict(top=210,height=75,font='font45',textcolor='FFCAD3DD'),
                dict(top=320,height=120,font='font75',textcolor='FFFFFFFF'),
                dict(top=455,height=70,font='font45',textcolor='FFCAD3DD'))
        for label,values in zip(labels,fields):
            for key,value in values.items():
                item=label.find(key)
                if item is None:item=ET.SubElement(label,key)
                item.text=str(value)
        for cid in ids:root.find(".//control[@id='%d']/top"%cid).text='600'
    after=[ET.tostring(n) for n in root.iter('control') if n.get('type')=='image']
    if after!=backgrounds:raise RuntimeError('Hintergrundprüfung fehlgeschlagen. Keine Änderung gespeichert.')
    ET.indent(root,space='    ')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def reload():subprocess.run(['kodi-send','--action=ReloadSkin()'],check=False)

def install():
    changes={SKIN/'custom_MiraPhone.xml':patch_xml((SKIN/'custom_MiraPhone.xml').read_bytes(),4),
             SKIN/'custom_MiraPhoneIncoming.xml':patch_xml((SKIN/'custom_MiraPhoneIncoming.xml').read_bytes(),2)}
    folder=BACKUPS/('phone-buttons-v14-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir(parents=True,mode=0o700);records=[]
    for i,(path,data) in enumerate(changes.items()):
        before=digest(path);saved=str(i)+'.bak'
        if before is not None:shutil.copy2(path,folder/saved)
        records.append(dict(path=str(path),before=before,backup=saved,after=hashlib.sha256(data).hexdigest()))
    (folder/'manifest.json').write_text(json.dumps(records,indent=2))
    try:
        for path,data in changes.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            temp=path.with_suffix('.v14.tmp');temp.write_bytes(data);temp.replace(path)
    except Exception:
        for item in records:
            path=Path(item['path'])
            if item['before'] is None:path.unlink(missing_ok=True)
            else:shutil.copy2(folder/item['backup'],path)
        raise
    LATEST.unlink(missing_ok=True);LATEST.symlink_to(folder.name)
    reload();print('Heller Buttonfokus installiert. Backup: '+str(folder))
    print('Buttonfokus und Popup-Typografie überarbeitet. Hintergrundgrafiken, Transparenz und Telefonlogik bleiben erhalten.')

def rollback():
    folder=LATEST.resolve(strict=True);records=json.loads((folder/'manifest.json').read_text())
    for item in records:
        if digest(Path(item['path']))!=item['after']:raise RuntimeError('Datei inzwischen geändert: '+item['path'])
    for item in records:
        path=Path(item['path'])
        if item['before'] is None:path.unlink(missing_ok=True)
        else:shutil.copy2(folder/item['backup'],path)
    reload();print('V14 zurückgenommen. Vorheriger Buttonfokus wieder aktiv.')

def backup_git():
    repo=HOME/'rpi-automotive-setup'
    def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True)
    if git('branch','--show-current').stdout.strip()!='main':raise RuntimeError('Nicht auf main.')
    git('fetch','origin');git('merge-base','--is-ancestor','origin/main','HEAD')
    mappings=[(SKIN/name,'mira/skin.estuary.custom/xml/'+name) for name in ('custom_MiraPhone.xml','custom_MiraPhoneIncoming.xml')]
    mappings += [(Path(__file__).resolve(),'tools/mira_phone_buttons_v14.py')]
    paths=[r for s,r in mappings];status=git('status','--porcelain','--',*paths).stdout
    if status.strip():raise RuntimeError('Exportziele haben lokale Änderungen:\n'+status)
    for source,relative in mappings:
        target=repo/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    git('add','--',*paths)
    result=subprocess.run(['git','-C',str(repo),'diff','--cached','--quiet','--',*paths])
    if result.returncode==1:print(git('commit','--only','-m','MIRA: Telefonbuttons mit hellem Flaechenfokus hervorheben','--',*paths).stdout)
    elif result.returncode:raise RuntimeError('Git-Diff fehlgeschlagen.')
    result=git('push','origin','main');print(result.stdout+result.stderr);print('GitHub-Sicherung abgeschlossen.')

if __name__=='__main__':
    try:
        if len(sys.argv)==1:install()
        elif sys.argv[1:]==['--rollback']:rollback()
        elif sys.argv[1:]==['--backup-git']:backup_git()
        else:raise RuntimeError('Optionen: --rollback oder --backup-git')
    except Exception as error:raise SystemExit('Abgebrochen: '+str(error))
