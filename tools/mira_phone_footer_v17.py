#!/usr/bin/env python3
"""MIRA V17: gut lesbare Anruf-Pill fuer das 800x480-Display."""
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
LATEST=BACKUPS/'phone-footer-v17-latest'
ASSETS={'mira/phone-footer-v17-normal.png': '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', 'mira/phone-footer-v17-focus.png': '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', 'mira/phone-footer-v17-receiver.png': 'iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAEUUlEQVR4nNWay4scVRTGf6dqRnSRkTiIBlw4IOIL8RVBQkRQcSEkWWRvUMGNCIJ7/wCzUhcqkrjX1azciNkoGQdxIUJcKIL4iMFADKKZfnwu7jnp2zXVU9X0o8YDRXV1n1v3+87rnntn4H8uVvelpLJh3NDMtAA8s4ukWlI1esWisbSR62AlWVhV0pNAnRcEFMC2mV2VVJjZcDlQ9xBJFpaX9IGaZUvS3TG2W/QJRCFpRdJ7DrAnaTDh6rnO75Juzcl3BT4sv54BHzZ4YMfvp3zsSlf4CzOTJ+QV4GtSjDdVmNA56c+d5cH1SmJmfeCqP7YhYMBRSbeZ2bCrMKqWwhtajjNgAKwBx/y7prVjIRIEwnrf+H2aReplD8FOwqhK4NIUY0sS0YeAuzyMlr64xYRh8XMkS7YFMiCF3fHK+5YvXs9XJX3vJXLQYkHr+/28ryOdeQCgNLMesOnPbWI6xt8L3NxFNcoJRBh9QgqNNtYc+vUTcEVZP7UsyUGGxb8FLtJuQYvm7nNfR7rtUOX7AEkfZT1RU/xvS1pT6qe6bewyAs83JHI0dn9K2vAx3e8PNGrsDih1m0PtbuyGGjV8T7h+J6twrWRe+HBCGIVXXnG9zjrRWolQkHSPpGsab68j7j92nc7B74pbr+WlmV0ATrtOVKhI0g1JNwKddaF7itKqXHh1+SGL+9wLL7hu516olSwXTlaAR0hdkFT6tf+8AGMkzlVIxP11/321W6QTxMPIJD3q1aifldYgccp19y2J8MK7lbIaefG3pMOu0zofNDoJiWsxoZgl9EFJF2vyQZIuSzoShJuAaI9VW1O25a2PEb28Pg58Chwkdawlow1QH3jVzN53AoWZDWreVZrZQNLDpI3Qqo/fBL6KMf6OknQOO/t2NQulw27xusokpcOxFdcds+aEd+TynaS3JD1Ymdum8cpeJAJYHYk8sc9LejoHno3dyMZe85zqabzn6kv6QtIbku7LiSyKxKAyecgZSQ9kY29Rar+reiH50WVIT9KXGhWKhXsigIRFdyS9Len+BvC5hDdzz/wo6ZDmdRY7gcROBUiVVH6fRv71+5v53DDDFtDM+pJWzGwbeA74jVRRYp8Mo7Oj2GNPc2STS7xnl+VniicnUTqJx4Cz/s6CBDomDQCzzFcbNjMnhNf0wsx+NbMXgWeALRLoOEOttd48ZC772DgP8pD6DDgKvAT8wm4ic5W5bcTNTFlI9czsDPAI8A7QY5zI3MjM/STBQyq88YeZvUbyyCbwF4lIkBmSWpA2rYLq9Baym/LTub5GPdEWcFzSHcCzwAngCLDOyIhRvSJXLPs8dKw3LQJvoyh1s0Xlu3VJxySdlfRzi7XgstKaM9YXLXUr6BMXVDpMSWvAUyTP3EkKl0PA7a7yD3DCzLZV+dt0Z3vZCC9IeVPzewkccJ3SzC5VwUOHBHLJyeDVqQq0DjzsEwJ1okrDtm//uWRW+Q9h+jY8CjWsngAAAABJRU5ErkJggg=='}

def put(node,key,value):
    child=node.find(key)
    if child is None:child=ET.SubElement(node,key)
    child.text=str(value)
    return child

def patch_footer(source):
    root=ET.fromstring(source)
    nodes=root.findall(".//include[@name='RNSE_GlobalFooter']")
    if root.tag=='include' and root.get('name')=='RNSE_GlobalFooter':nodes=[root]
    if len(nodes)!=1:raise RuntimeError('Gemeinsamer Footer nicht eindeutig.')
    footer=nodes[0]
    images=[n for n in footer.iter('control') if n.findtext('texture')=='mira/phone-footer-v16-normal.png']
    if len(images)!=1:raise RuntimeError('Erwarteter V16-Footer fehlt; nichts geändert.')
    parents={child:parent for parent in footer.iter() for child in parent}
    pill=parents[images[0]]
    if tuple(pill.findtext(k) for k in ('left','top','width','height'))!=('0','4','350','74'):
        raise RuntimeError('Abweichende Pill-Geometrie; nichts geändert.')
    put(pill,'left',-140);put(pill,'width',490)
    backgrounds=[n for n in pill.findall('control') if n.findtext('texture','').startswith('mira/phone-footer-v16-')]
    if len(backgrounds)!=2:raise RuntimeError('Pill-Hintergründe sind nicht eindeutig.')
    for image in backgrounds:
        put(image,'width',490)
        texture=image.find('texture');texture.text=texture.text.replace('v16','v17')
    icons=[n for n in pill.findall('control') if n.findtext('texture')=='home/mmi_icons_v1/phone.png']
    if len(icons)!=1:raise RuntimeError('Hörersymbol fehlt.')
    icon=icons[0]
    for key,value in dict(left=15,top=16,width=42,height=42,texture='mira/phone-footer-v17-receiver.png').items():put(icon,key,value)
    labels=pill.findall("control[@type='label']")
    if len(labels)!=4:raise RuntimeError('Pill-Beschriftungen haben einen unbekannten Stand.')
    for label in labels:
        name='MiraPhoneCallName' in label.findtext('label','')
        for key,value in dict(left=70 if name else 338,width=254 if name else 138,font='font45').items():put(label,key,value)
        text=label.find('label');text.text='[B]'+text.text.replace('[B]','').replace('[/B]','')+'[/B]'
    # Enlarge the invisible hit area to include the full pill, with its right edge fixed.
    button=footer.find(".//control[@id='$PARAM[footer_right_id]']")
    if button is None or button.findtext('width')!='520' or button.findtext('onclick')!='RunScript(/home/pi/.kodi/userdata/scripts/mira_phone_footer.py)':
        raise RuntimeError('Unerwartete Footer-Softkey-Belegung.')
    put(button,'width',660)
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
    folder=BACKUPS/('phone-footer-v17-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir(parents=True,mode=0o700);records=[]
    for i,(path,data) in enumerate(changes.items()):
        before=digest(path);saved=str(i)+'.bak'
        if before is not None:shutil.copy2(path,folder/saved)
        records.append(dict(path=str(path),before=before,backup=saved,after=hashlib.sha256(data).hexdigest()))
    (folder/'manifest.json').write_text(json.dumps(records,indent=2))
    try:
        for path,data in changes.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            temp=path.with_suffix('.v17.tmp');temp.write_bytes(data);temp.replace(path)
    except Exception:
        for item in records:
            path=Path(item['path'])
            if item['before'] is None:path.unlink(missing_ok=True)
            else:shutil.copy2(folder/item['backup'],path)
        raise
    LATEST.unlink(missing_ok=True);LATEST.symlink_to(folder.name)
    reload();print('V17 installiert: breitere Anruf-Pill, größere Schrift und kräftiges Hörersymbol.')
    print('Backup: '+str(folder));print('Keine Anrufe gestartet oder verändert. Uhrzeit, Empfang und Akku bleiben an ihrem Platz.')

def rollback():
    folder=LATEST.resolve(strict=True);records=json.loads((folder/'manifest.json').read_text())
    for item in records:
        if digest(Path(item['path']))!=item['after']:raise RuntimeError('Datei inzwischen geändert: '+item['path'])
    for item in records:
        path=Path(item['path'])
        if item['before'] is None:path.unlink(missing_ok=True)
        else:shutil.copy2(folder/item['backup'],path)
    reload();print('V17 zurückgenommen; vorheriger Footer wieder aktiv.')

def backup_git():
    repo=HOME/'rpi-automotive-setup'
    def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True)
    if git('branch','--show-current').stdout.strip()!='main':raise RuntimeError('Nicht auf main.')
    git('fetch','origin');git('merge-base','--is-ancestor','origin/main','HEAD')
    mappings=[(SKIN/'Includes_RNSE_AppShell.xml','mira/skin.estuary.custom/xml/Includes_RNSE_AppShell.xml')]
    mappings += [(SKIN.parent/'media'/relative,'mira/skin.estuary.custom/media/'+relative) for relative in ASSETS]
    mappings += [(Path(__file__).resolve(),'tools/mira_phone_footer_v17.py')]
    paths=[r for s,r in mappings];status=git('status','--porcelain','--',*paths).stdout
    if status.strip():raise RuntimeError('Exportziele haben lokale Änderungen:\n'+status)
    for source,relative in mappings:
        target=repo/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    git('add','--',*paths)
    result=subprocess.run(['git','-C',str(repo),'diff','--cached','--quiet','--',*paths])
    if result.returncode==1:print(git('commit','--only','-m','MIRA: Anruf-Pill fuer RNS-E besser lesbar gestaltet','--',*paths).stdout)
    elif result.returncode:raise RuntimeError('Git-Diff fehlgeschlagen.')
    result=git('push','origin','main');print(result.stdout+result.stderr);print('GitHub-Sicherung abgeschlossen.')

if __name__=='__main__':
    try:
        if len(sys.argv)==1:install()
        elif sys.argv[1:]==['--rollback']:rollback()
        elif sys.argv[1:]==['--backup-git']:backup_git()
        else:raise RuntimeError('Optionen: --rollback oder --backup-git')
    except Exception as error:raise SystemExit('Abgebrochen: '+str(error))
