#!/usr/bin/env python3
"""MIRA V16: zentraler Telefon-Softkey und Anruf-Pill im gemeinsamen Footer."""
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
LATEST=BACKUPS/'phone-footer-v16-latest'
ROUTER="# MIRA_PHONE_FOOTER_V16\nimport xbmc\nimport xbmcgui\n\nHOME = xbmcgui.Window(10000)\nPHONE = xbmcgui.Window(11189)\n\ndef destination(connected, present):\n    return 1189 if connected == 'true' or present == 'true' else 1160\n\ndef main():\n    target = destination(HOME.getProperty('RNSE.Phone.Connected'),\n                         PHONE.getProperty('MiraPhoneCallPresent'))\n    if target == 1160:\n        xbmc.executebuiltin('ActivateWindow(1160)')\n        return\n    # Entering via the footer does not arm the popup's automatic return rule.\n    was_phone = xbmcgui.getCurrentWindowId() == 11189\n    token = PHONE.getProperty('MiraPhoneRefreshToken')\n    if not was_phone:\n        xbmc.executebuiltin('ActivateWindow(1189)')\n    if PHONE.getProperty('MiraPhoneCallPresent') != 'true':\n        return  # The existing onload action owns normal list focus.\n    monitor = xbmc.Monitor()\n    entered = was_phone\n    for _ in range(50):\n        current = xbmcgui.getCurrentWindowId()\n        if entered and current != 11189:\n            return\n        entered = entered or current == 11189\n        ready = was_phone or PHONE.getProperty('MiraPhoneRefreshToken') != token\n        if ready and current == 11189 and xbmcgui.getCurrentWindowDialogId() == 9999:\n            if PHONE.getProperty('MiraPhoneCallPresent') != 'true':\n                return\n            control = 9652 if PHONE.getProperty('MiraPhoneCallCanAnswer') == 'true' else 9651\n            if xbmc.getCondVisibility('Control.IsVisible(%d)' % control):\n                xbmc.executebuiltin('SetFocus(%d)' % control)\n                return\n        if monitor.waitForAbort(0.1):\n            return\n\nif __name__ == '__main__':\n    main()\n"
ASSETS={'mira/phone-footer-v16-normal.png': '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', 'mira/phone-footer-v16-focus.png': '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'}

PRESENT='String.IsEqual(Window(11189).Property(MiraPhoneCallPresent),true)'
CONNECTED='String.IsEqual(Window(Home).Property(RNSE.Phone.Connected),true)'
FOCUSED='Control.HasFocus($PARAM[footer_right_id])'

def put(node,key,value):
    child=node.find(key)
    if child is None:child=ET.SubElement(node,key)
    child.text=str(value)
    return child

def control(parent,kind,**values):
    node=ET.SubElement(parent,'control',{'type':kind})
    for key,value in values.items():put(node,key,value)
    return node

def patch_footer(source):
    root=ET.fromstring(source)
    nodes=root.findall(".//include[@name='RNSE_GlobalFooter']")
    if root.tag=='include' and root.get('name')=='RNSE_GlobalFooter':nodes=[root]
    if len(nodes)!=1:raise RuntimeError('Gemeinsamer Footer nicht eindeutig gefunden.')
    footer=nodes[0]
    buttons=footer.findall(".//control[@id='$PARAM[footer_right_id]']")
    if len(buttons)!=1:raise RuntimeError('Rechter Footer-Softkey fehlt.')
    button=buttons[0]
    actions=button.findall('onclick')
    if len(actions)!=1 or actions[0].text!='ActivateWindow(1160)':
        raise RuntimeError('Unerwartete Footer-Belegung; nichts geändert.')
    actions[0].text='RunScript(/home/pi/.kodi/userdata/scripts/mira_phone_footer.py)'
    parents={child:parent for parent in footer.iter() for child in parent}
    operators=[n for n in footer.iter('control') if n.findtext('label')=='[B]$INFO[Window(Home).Property(RNSE.Phone.Operator)][/B]']
    if len(operators)!=2:raise RuntimeError('Netzbetreiber-Anzeigen haben einen unbekannten Stand.')
    visual=parents[parents[operators[0]]]
    if (visual.findtext('width'),visual.findtext('height'))!=('520','82'):
        raise RuntimeError('Footer-Geometrie ist abweichend.')
    for node in operators:put(node,'visible','!'+PRESENT)
    disconnected=[n for n in footer.iter('control') if n.findtext('label')=='[B]Kein Telefon[/B]']
    if len(disconnected)!=1:raise RuntimeError('Anzeige für getrenntes Telefon fehlt.')
    put(disconnected[0],'visible','!'+CONNECTED+' + !'+PRESENT)
    pill=control(visual,'group',left=0,top=4,width=350,height=74,visible=PRESENT)
    for focused in (False,True):
        image=control(pill,'image',left=0,top=0,width=350,height=74,
                      texture='mira/phone-footer-v16-'+('focus' if focused else 'normal')+'.png',
                      visible=FOCUSED if focused else '!'+FOCUSED)
    icon=control(pill,'image',left=14,top=21,width=34,height=32,aspectratio='keep',texture='home/mmi_icons_v1/phone.png')
    icon.find('texture').set('colordiffuse','FFFFFFFF')
    control(pill,'label',left=60,top=0,width=158,height=74,font='font35',textcolor='FFFFFFFF',
            aligny='center',scroll='false',label='[B]$INFO[Window(11189).Property(MiraPhoneCallName)][/B]')
    empty='String.IsEmpty(Window(11189).Property(MiraPhoneCallDuration))'
    duration='!'+empty
    incoming='String.IsEqual(Window(11189).Property(MiraPhoneCallCanAnswer),true)'
    for text,condition in (('[B]$INFO[Window(11189).Property(MiraPhoneCallDuration)][/B]',duration),
                           ('Klingelt',empty+' + '+incoming),
                           ('Anruf',empty+' + !'+incoming)):
        control(pill,'label',left=223,top=0,width=113,height=74,font='font35',textcolor='FFFFFFFF',
                align='right',aligny='center',scroll='false',label=text,visible=condition)
    ET.indent(root,space='    ')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def reload():subprocess.run(['kodi-send','--action=ReloadSkin()'],check=False)

def install():
    include_path=SKIN/'Includes_RNSE_AppShell.xml'
    helper=HOME/'.kodi/userdata/scripts/mira_phone_footer.py'
    if helper.exists():raise RuntimeError('V16-Helfer existiert bereits; nichts geändert.')
    for name in ('mira_phone_ui.py','mira_phone_global.py'):
        if not (helper.parent/name).is_file():raise RuntimeError('Telefon-Grundlage fehlt: '+name)
    changes={include_path:patch_footer(include_path.read_bytes()), helper:ROUTER.encode()}
    for relative,encoded in ASSETS.items():
        path=SKIN.parent/'media'/relative
        if path.exists():raise RuntimeError('Neue Buttontextur existiert bereits: '+str(path))
        data=base64.b64decode(encoded,validate=True)
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise RuntimeError('Ungültige Grafik.')
        changes[path]=data
    folder=BACKUPS/('phone-footer-v16-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir(parents=True,mode=0o700);records=[]
    for i,(path,data) in enumerate(changes.items()):
        before=digest(path);saved=str(i)+'.bak'
        if before is not None:shutil.copy2(path,folder/saved)
        records.append(dict(path=str(path),before=before,backup=saved,after=hashlib.sha256(data).hexdigest()))
    (folder/'manifest.json').write_text(json.dumps(records,indent=2))
    try:
        for path,data in changes.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            temp=path.with_suffix('.v16.tmp');temp.write_bytes(data);temp.replace(path)
    except Exception:
        for item in records:
            path=Path(item['path'])
            if item['before'] is None:path.unlink(missing_ok=True)
            else:shutil.copy2(folder/item['backup'],path)
        raise
    LATEST.unlink(missing_ok=True);LATEST.symlink_to(folder.name)
    reload();print('V16 installiert: globaler Telefon-Softkey und grüne Anruf-Pill im Footer.')
    print('Backup: '+str(folder));print('Keine Anrufe gestartet oder verändert. Uhrzeit, Empfang und Akku bleiben an ihrem Platz.')

def rollback():
    folder=LATEST.resolve(strict=True);records=json.loads((folder/'manifest.json').read_text())
    for item in records:
        if digest(Path(item['path']))!=item['after']:raise RuntimeError('Datei inzwischen geändert: '+item['path'])
    for item in records:
        path=Path(item['path'])
        if item['before'] is None:path.unlink(missing_ok=True)
        else:shutil.copy2(folder/item['backup'],path)
    reload();print('V16 zurückgenommen; vorheriger Footer wieder aktiv.')

def backup_git():
    repo=HOME/'rpi-automotive-setup'
    def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True)
    if git('branch','--show-current').stdout.strip()!='main':raise RuntimeError('Nicht auf main.')
    git('fetch','origin');git('merge-base','--is-ancestor','origin/main','HEAD')
    mappings=[(SKIN/'Includes_RNSE_AppShell.xml','mira/skin.estuary.custom/xml/Includes_RNSE_AppShell.xml'),
              (HOME/'.kodi/userdata/scripts/mira_phone_footer.py','mira/userdata/scripts/mira_phone_footer.py')]
    mappings += [(SKIN.parent/'media'/relative,'mira/skin.estuary.custom/media/'+relative) for relative in ASSETS]
    mappings += [(Path(__file__).resolve(),'tools/mira_phone_footer_v16.py')]
    paths=[r for s,r in mappings];status=git('status','--porcelain','--',*paths).stdout
    if status.strip():raise RuntimeError('Exportziele haben lokale Änderungen:\n'+status)
    for source,relative in mappings:
        target=repo/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    git('add','--',*paths)
    result=subprocess.run(['git','-C',str(repo),'diff','--cached','--quiet','--',*paths])
    if result.returncode==1:print(git('commit','--only','-m','MIRA: Globaler Telefon-Softkey und Anrufstatus im Footer','--',*paths).stdout)
    elif result.returncode:raise RuntimeError('Git-Diff fehlgeschlagen.')
    result=git('push','origin','main');print(result.stdout+result.stderr);print('GitHub-Sicherung abgeschlossen.')

if __name__=='__main__':
    try:
        if len(sys.argv)==1:install()
        elif sys.argv[1:]==['--rollback']:rollback()
        elif sys.argv[1:]==['--backup-git']:backup_git()
        else:raise RuntimeError('Optionen: --rollback oder --backup-git')
    except Exception as error:raise SystemExit('Abgebrochen: '+str(error))
