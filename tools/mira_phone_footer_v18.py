#!/usr/bin/env python3
"""MIRA V18: kontextabhaengiger Footer mit Platz fuer Rufnummern."""
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
LATEST=BACKUPS/'phone-footer-v18-latest'
ROUTER="# MIRA_PHONE_FOOTER_V18\nimport xbmc\nimport xbmcgui\n\nHOME = xbmcgui.Window(10000)\nPHONE = xbmcgui.Window(11189)\n\ndef destination(connected, present):\n    return 1189 if connected == 'true' or present == 'true' else 1160\n\ndef main():\n    if xbmcgui.getCurrentWindowId() == 11189:\n        xbmc.executebuiltin('ActivateWindow(1160)')\n        return\n    target = destination(HOME.getProperty('RNSE.Phone.Connected'),\n                         PHONE.getProperty('MiraPhoneCallPresent'))\n    if target == 1160:\n        xbmc.executebuiltin('ActivateWindow(1160)')\n        return\n    # Entering via the footer does not arm the popup's automatic return rule.\n    was_phone = xbmcgui.getCurrentWindowId() == 11189\n    token = PHONE.getProperty('MiraPhoneRefreshToken')\n    if not was_phone:\n        xbmc.executebuiltin('ActivateWindow(1189)')\n    if PHONE.getProperty('MiraPhoneCallPresent') != 'true':\n        return  # The existing onload action owns normal list focus.\n    monitor = xbmc.Monitor()\n    entered = was_phone\n    for _ in range(50):\n        current = xbmcgui.getCurrentWindowId()\n        if entered and current != 11189:\n            return\n        entered = entered or current == 11189\n        ready = was_phone or PHONE.getProperty('MiraPhoneRefreshToken') != token\n        if ready and current == 11189 and xbmcgui.getCurrentWindowDialogId() == 9999:\n            if PHONE.getProperty('MiraPhoneCallPresent') != 'true':\n                return\n            control = 9652 if PHONE.getProperty('MiraPhoneCallCanAnswer') == 'true' else 9651\n            if xbmc.getCondVisibility('Control.IsVisible(%d)' % control):\n                xbmc.executebuiltin('SetFocus(%d)' % control)\n                return\n        if monitor.waitForAbort(0.1):\n            return\n\nif __name__ == '__main__':\n    main()\n"
OLD_ROUTER_HASH='2aa113b51b614b7fdf8d39b63290d34f1413db1dc58211a04fd593cb478bd323'
ASSETS={'mira/phone-footer-v18-normal.png': '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', 'mira/phone-footer-v18-focus.png': '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'}

PRESENT='String.IsEqual(Window(11189).Property(MiraPhoneCallPresent),true)'
CONNECTED='String.IsEqual(Window(Home).Property(RNSE.Phone.Connected),true)'
STATUS='Window(11189).Property(MiraPhoneCallStatus)'
DURATION='Window(11189).Property(MiraPhoneCallDuration)'
HELD='String.IsEqual('+STATUS+',Anruf gehalten)'
OUTGOING='[String.IsEqual('+STATUS+',Verbindung wird aufgebaut …) | String.IsEqual('+STATUS+',Es klingelt …)]'
HAS_TIME='!String.IsEmpty('+DURATION+')'
SHOW=PRESENT+' + !Window.IsActive(1189) + ['+HAS_TIME+' | '+HELD+' | '+OUTGOING+']'
IS_NUMBER='!String.IsEmpty(Window(11189).Property(MiraPhoneCallNumber)) + String.IsEqual(Window(11189).Property(MiraPhoneCallName),$INFO[Window(11189).Property(MiraPhoneCallNumber)])'

def put(node,key,value):
    child=node.find(key)
    if child is None:child=ET.SubElement(node,key)
    child.text=str(value)
    return child

def make_label(parent,text,left,width,font,condition):
    node=ET.SubElement(parent,'control',{'type':'label'})
    for key,value in dict(left=left,top=0,width=width,height=74,font=font,textcolor='FFFFFFFF',aligny='center',scroll='false',label='[B]'+text+'[/B]',visible=condition).items():put(node,key,value)
    return node

def patch_footer(source):
    root=ET.fromstring(source)
    found=root.findall(".//include[@name='RNSE_GlobalFooter']")
    if root.tag=='include' and root.get('name')=='RNSE_GlobalFooter':found=[root]
    if len(found)!=1:raise RuntimeError('Gemeinsamer Footer nicht eindeutig.')
    footer=found[0]
    images=[n for n in footer.iter('control') if n.findtext('texture')=='mira/phone-footer-v17-normal.png']
    if len(images)!=1:raise RuntimeError('Erwarteter V17-Footer fehlt; nichts geändert.')
    parents={child:parent for parent in footer.iter() for child in parent}
    pill=parents[images[0]]
    if tuple(pill.findtext(k) for k in ('left','top','width','height','visible'))!=('-140','4','490','74',PRESENT):
        raise RuntimeError('Pill-Geometrie oder Sichtbarkeit hat einen unbekannten Stand.')
    put(pill,'left',-164);put(pill,'width',514);put(pill,'visible',SHOW)
    backgrounds=[n for n in pill.findall('control') if n.findtext('texture','').startswith('mira/phone-footer-v17-') and 'receiver' not in n.findtext('texture','')]
    if len(backgrounds)!=2:raise RuntimeError('Pill-Hintergründe sind nicht eindeutig.')
    for image in backgrounds:
        put(image,'width',514)
        image.find('texture').text=image.findtext('texture').replace('v17','v18')
    labels=pill.findall("control[@type='label']")
    if len(labels)!=4:raise RuntimeError('Pill-Beschriftungen haben einen unbekannten Stand.')
    for node in labels:pill.remove(node)
    make_label(pill,'$INFO[Window(11189).Property(MiraPhoneCallName)]',66,282,'font45','!['+IS_NUMBER+']')
    make_label(pill,'$INFO[Window(11189).Property(MiraPhoneCallNumber)]',66,282,'font35',IS_NUMBER)
    # Two dashes mark held calls. Outgoing calls have not started their timer yet.
    for text,condition in (('--',HELD),('$INFO['+DURATION+']','!'+HELD+' + '+HAS_TIME),('…','!'+HELD+' + String.IsEmpty('+DURATION+')')):
        node=make_label(pill,text,362,138,'font45',condition)
        put(node,'align','right')
    operators=[n for n in footer.iter('control') if 'RNSE.Phone.Operator' in n.findtext('label','')]
    if len(operators)!=2:raise RuntimeError('Netzbetreiber-Anzeigen sind nicht eindeutig.')
    for node in operators:
        if node.findtext('visible')!='!'+PRESENT:raise RuntimeError('Abweichende Netzbetreiber-Sichtbarkeit.')
        put(node,'visible','!['+SHOW+']')
    missing=[n for n in footer.iter('control') if n.findtext('label')=='[B]Kein Telefon[/B]']
    if len(missing)!=1:raise RuntimeError('Anzeige für getrenntes Telefon fehlt.')
    put(missing[0],'visible','!'+CONNECTED+' + !['+SHOW+']')
    button=footer.find(".//control[@id='$PARAM[footer_right_id]']")
    if button is None or button.findtext('width')!='660' or button.findtext('onclick')!='RunScript(/home/pi/.kodi/userdata/scripts/mira_phone_footer.py)':
        raise RuntimeError('Unerwartete Footer-Softkey-Belegung.')
    put(button,'width',684)
    ET.indent(root,space='    ')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def reload():subprocess.run(['kodi-send','--action=ReloadSkin()'],check=False)

def install():
    include_path=SKIN/'Includes_RNSE_AppShell.xml'
    helper=HOME/'.kodi/userdata/scripts/mira_phone_footer.py'
    if digest(helper)!=OLD_ROUTER_HASH:raise RuntimeError('Footer-Helfer entspricht nicht V16/V18; nichts geändert.')
    calls=(helper.parent/'mira_phone_calls.py').read_text()
    for required in ('Anruf gehalten','Verbindung wird aufgebaut …','Es klingelt …'):
        if required not in calls:raise RuntimeError('Anrufstatus hat einen unbekannten Stand; nichts geändert.')
    changes={include_path:patch_footer(include_path.read_bytes()),helper:ROUTER.encode()}
    for relative,encoded in ASSETS.items():
        path=SKIN.parent/'media'/relative
        if path.exists():raise RuntimeError('Neue Buttontextur existiert bereits: '+str(path))
        data=base64.b64decode(encoded,validate=True)
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise RuntimeError('Ungültige Grafik.')
        changes[path]=data
    folder=BACKUPS/('phone-footer-v18-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir(parents=True,mode=0o700);records=[]
    for i,(path,data) in enumerate(changes.items()):
        before=digest(path);saved=str(i)+'.bak'
        if before is not None:shutil.copy2(path,folder/saved)
        records.append(dict(path=str(path),before=before,backup=saved,after=hashlib.sha256(data).hexdigest()))
    (folder/'manifest.json').write_text(json.dumps(records,indent=2))
    try:
        for path,data in changes.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            temp=path.with_suffix('.v18.tmp');temp.write_bytes(data);temp.replace(path)
    except Exception:
        for item in records:
            path=Path(item['path'])
            if item['before'] is None:path.unlink(missing_ok=True)
            else:shutil.copy2(folder/item['backup'],path)
        raise
    LATEST.unlink(missing_ok=True);LATEST.symlink_to(folder.name)
    reload();print('V18 installiert: kontextabhängige Anruf-Pill und Bluetooth-Shortcut in der Telefon-App.')
    print('Backup: '+str(folder));print('Keine Anrufe gestartet oder verändert. Uhrzeit, Empfang und Akku bleiben an ihrem Platz.')

def rollback():
    folder=LATEST.resolve(strict=True);records=json.loads((folder/'manifest.json').read_text())
    for item in records:
        if digest(Path(item['path']))!=item['after']:raise RuntimeError('Datei inzwischen geändert: '+item['path'])
    for item in records:
        path=Path(item['path'])
        if item['before'] is None:path.unlink(missing_ok=True)
        else:shutil.copy2(folder/item['backup'],path)
    reload();print('V18 zurückgenommen; vorheriger Footer wieder aktiv.')

def backup_git():
    repo=HOME/'rpi-automotive-setup'
    def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True)
    if git('branch','--show-current').stdout.strip()!='main':raise RuntimeError('Nicht auf main.')
    git('fetch','origin');git('merge-base','--is-ancestor','origin/main','HEAD')
    mappings=[(SKIN/'Includes_RNSE_AppShell.xml','mira/skin.estuary.custom/xml/Includes_RNSE_AppShell.xml'),
              (HOME/'.kodi/userdata/scripts/mira_phone_footer.py','mira/userdata/scripts/mira_phone_footer.py')]
    mappings += [(SKIN.parent/'media'/relative,'mira/skin.estuary.custom/media/'+relative) for relative in ASSETS]
    mappings += [(Path(__file__).resolve(),'tools/mira_phone_footer_v18.py')]
    paths=[r for s,r in mappings];status=git('status','--porcelain','--',*paths).stdout
    if status.strip():raise RuntimeError('Exportziele haben lokale Änderungen:\n'+status)
    for source,relative in mappings:
        target=repo/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    git('add','--',*paths)
    result=subprocess.run(['git','-C',str(repo),'diff','--cached','--quiet','--',*paths])
    if result.returncode==1:print(git('commit','--only','-m','MIRA: Kontextabhaengige Anruf-Pill und Bluetooth-Zugang im Telefonfenster','--',*paths).stdout)
    elif result.returncode:raise RuntimeError('Git-Diff fehlgeschlagen.')
    result=git('push','origin','main');print(result.stdout+result.stderr);print('GitHub-Sicherung abgeschlossen.')

if __name__=='__main__':
    try:
        if len(sys.argv)==1:install()
        elif sys.argv[1:]==['--rollback']:rollback()
        elif sys.argv[1:]==['--backup-git']:backup_git()
        else:raise RuntimeError('Optionen: --rollback oder --backup-git')
    except Exception as error:raise SystemExit('Abgebrochen: '+str(error))
