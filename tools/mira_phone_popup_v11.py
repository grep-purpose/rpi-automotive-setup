#!/usr/bin/env python3
"""MIRA Telefon V11: globales Anruf-Pop-up im vorhandenen USB-Dialogstil."""
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
import xml.etree.ElementTree as ET
HOME=Path.home()
SKIN=HOME/'.kodi/addons/skin.estuary.custom/xml'
SCRIPTS=HOME/'.kodi/userdata/scripts'
KEYMAP=HOME/'.kodi/userdata/keymaps/zzz_mira_phone_popup.xml'
ROOT=HOME/'.cache/mira-phone'
STOP=ROOT/'popup-v11.stop'
BACKUPS=HOME/'.kodi/userdata/mira-backups'
LATEST=BACKUPS/'phone-popup-v11-latest'
PAYLOAD={'mira_phone_call_watch.py': '# MIRA_PHONE_POPUP_V11\nfrom mira_phone_global import main\nmain()\n', 'mira_phone_popup.py': "# MIRA_PHONE_POPUP_V11\nfrom pathlib import Path\nimport fcntl\nimport sys\nimport xbmc\nimport xbmcgui\nfrom mira_phone_calls import backend\n\nHOME=xbmcgui.Window(10000)\nROOT=Path.home()/'.cache/mira-phone'\nBASE=Path(__file__).parent\n\ndef close():xbmc.executebuiltin('Dialog.Close(1190)')\n\ndef main():\n    action=sys.argv[1] if len(sys.argv)>1 else 'dismiss'\n    path=sys.argv[2] if len(sys.argv)>2 else HOME.getProperty('MiraPhonePopupPath')\n    if action in ('dismiss','closed'):\n        if path:HOME.setProperty('MiraPhonePopupSuppressed',path)\n        if action=='dismiss':close()\n        return\n    if action not in ('answer','hangup') or not path:return\n    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)\n    with (ROOT/'call-action.lock').open('a') as lock:\n        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)\n        except BlockingIOError:return\n        # The path is frozen in the button action; the backend rechecks it.\n        result=backend({'action':action,'path':path})\n        if not result.get('ok'):\n            xbmcgui.Dialog().notification('Telefon',result.get('error','Telefonaktion fehlgeschlagen.'))\n            return\n        HOME.setProperty('MiraPhonePopupSuppressed',path)\n        close()\n        if action=='answer':\n            phone=xbmcgui.Window(11189)\n            was_phone=xbmcgui.getCurrentWindowId()==11189\n            old_token=phone.getProperty('MiraPhoneRefreshToken')\n            xbmc.executebuiltin('ActivateWindow(1189)')\n            monitor=xbmc.Monitor()\n            for _ in range(50):\n                ready=was_phone or phone.getProperty('MiraPhoneRefreshToken')!=old_token\n                if (ready and xbmcgui.getCurrentWindowId()==11189\n                        and xbmcgui.getCurrentWindowDialogId()==9999\n                        and phone.getProperty('MiraPhoneCallPresent')\n                        and not phone.getProperty('MiraPhoneCallCanAnswer')):\n                    xbmc.executebuiltin('SetFocus(9651)')\n                    return\n                if monitor.waitForAbort(0.1):return\n\nif __name__=='__main__':main()\n", 'mira_phone_global.py': "# MIRA_PHONE_POPUP_V11\nfrom pathlib import Path\nimport fcntl\nimport json\nimport re\nimport time\nimport xbmc\nimport xbmcgui\nimport mira_phone_calls as calls\nfrom mira_phone_cache import path as cache_path\n\nHOME=xbmcgui.Window(10000)\nPHONE=xbmcgui.Window(11189)\nBASE=Path(__file__).parent\nROOT=Path.home()/'.cache/mira-phone'\nSTOP=ROOT/'popup-v11.stop'\nDIALOG=1190\n\ndef visible():\n    return xbmc.getCondVisibility('Window.IsVisible(1190)')\n\ndef close():\n    if visible():xbmc.executebuiltin('Dialog.Close(1190)')\n\ndef contact_file(call):\n    match=re.search(r'/dev_([0-9A-Fa-f_]{17})(?:/|$)',call.get('path',''))\n    if match:\n        return str(cache_path(match[1].replace('_',':')))\n    # Test calls contain no telephone number and use a fixed synthetic name.\n    return ''\n\ndef display(call):\n    number=call.get('number','')\n    name=calls.find_name(number)\n    remote=call.get('name','').strip()\n    if number and calls.number_key(remote)==calls.number_key(number):remote=''\n    name=name or remote or number or 'Unbekannte Nummer'\n    detail=number if number and calls.number_key(name)!=calls.number_key(number) else ''\n    return name,detail\n\nclass PopupState:\n    def __init__(self):\n        self.path=''\n        self.requested=0\n        self.errors=0\n    def apply(self,data):\n        if not data.get('ok'):\n            self.errors+=1\n            if self.errors>=3:close()\n            return\n        self.errors=0\n        incoming=next((c for c in data.get('calls',[]) if c.get('state')=='incoming'),None)\n        if incoming is None:\n            close()\n            self.path='';self.requested=0\n            HOME.clearProperty('MiraPhonePopupSuppressed')\n            return\n        path=incoming['path']\n        if self.path!=path:\n            close();self.path=path;self.requested=0\n        if HOME.getProperty('MiraPhonePopupSuppressed')==path:\n            close();return\n        name,detail=display(incoming)\n        HOME.setProperty('MiraPhonePopupName',name)\n        HOME.setProperty('MiraPhonePopupDetail',detail)\n        HOME.setProperty('MiraPhonePopupPath',path)\n        if not visible() and time.monotonic()-self.requested>2:\n            self.requested=time.monotonic()\n            xbmc.executebuiltin('ActivateWindow(1190)')\n\ndef main():\n    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)\n    with (ROOT/'call-watch.lock').open('a') as lock:\n        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)\n        except BlockingIOError:return\n        if STOP.exists():return\n        monitor=xbmc.Monitor();started={};state=PopupState()\n        HOME.clearProperty('MiraPhonePopupSuppressed')\n        HOME.setProperty('MiraPhoneGlobalRunning','true')\n        try:\n            while not monitor.abortRequested() and not STOP.exists():\n                data=calls.backend({'action':'status'})\n                if data.get('ok'):\n                    entries=data.get('calls',[])\n                    selected=next((c for c in entries if c.get('path')==PHONE.getProperty('MiraPhoneCallPath')),entries[0] if entries else {})\n                    PHONE.setProperty('MiraPhoneCallContactsFile',contact_file(selected))\n                calls.update(data,started)\n                # Popup caller information can differ from an already active call.\n                incoming=next((c for c in data.get('calls',[]) if c.get('state')=='incoming'),None)\n                if incoming:\n                    PHONE.setProperty('MiraPhoneCallContactsFile',contact_file(incoming))\n                state.apply(data)\n                if monitor.waitForAbort(0.6 if data.get('calls') else 1):break\n        except Exception:\n            xbmc.log('[MIRA Phone] Globale Anrufanzeige beendet; keine Anrufdaten protokolliert.',xbmc.LOGERROR)\n        finally:\n            close()\n            HOME.clearProperty('MiraPhoneGlobalRunning')\n\nif __name__=='__main__':main()\n"}
CALLS_V10_HASH='93550396c001d4ebb841823dc32be8683bbe58ebaefe2af92e55ef4773dee9e6'
def put(node,key,value):
    item=node.find(key)
    if item is None:item=ET.SubElement(node,key)
    item.text=str(value);return item

def build_popup(source):
    root=ET.fromstring(source)
    if root.get('id')!='1167' or root.get('type')!='dialog':raise RuntimeError('USB-Pop-up hat einen unerwarteten Aufbau.')
    controls=root.find('controls')
    labels=controls.findall("control[@type='label']")
    buttons=controls.findall("control[@type='button']")
    if len(labels)!=3 or [b.get('id') for b in buttons]!=['9170','9171']:
        raise RuntimeError('USB-Pop-up enthält unerwartete Steuerelemente.')
    root.set('id','1190')
    for key in ('onload','onunload','onback','visible'):
        for child in list(root.findall(key)):root.remove(child)
    put(root,'defaultcontrol',9660).set('always','true')
    put(root,'onback','RunScript(%s,dismiss)'%(SCRIPTS/'mira_phone_popup.py'))
    # The underlying footer stays visible and is drawn only by its own window.
    shades=[n for n in controls.findall("control[@type='image']") if n.findtext('left')=='0' and n.findtext('top')=='0']
    if len(shades)!=1:raise RuntimeError('Abdunkelung nicht eindeutig.')
    put(shades[0],'height',1020)
    put(labels[0],'label','Eingehender Anruf');put(labels[0],'font','font55')
    put(labels[1],'label','[B]$INFO[Window(Home).Property(MiraPhonePopupName)][/B]')
    put(labels[1],'textcolor','FFFFFFFF');put(labels[1],'font','font75');put(labels[1],'top',330);put(labels[1],'height',120);put(labels[1],'scroll','true')
    put(labels[2],'label','$INFO[Window(Home).Property(MiraPhonePopupDetail)]')
    put(labels[2],'top',475);put(labels[2],'scroll','true')
    for button,cid,label,action,normal,focused in (
        (buttons[0],9660,'Annehmen','answer','FF10CE50','FF56F080'),
        (buttons[1],9661,'Ablehnen','hangup','FFCE3038','FFFF5050')):
        button.set('id',str(cid));put(button,'label','[B]'+label+'[/B]')
        put(button,'focusedcolor','FF10151C')
        for key,color in (('texturenofocus',normal),('texturefocus',focused)):
            item=put(button,key,'mira/phone-call-v4.png');item.attrib.clear();item.set('colordiffuse',color)
        for key in ('onup','ondown','onleft','onright'):put(button,key,9661 if cid==9660 else 9660)
        for old in list(button.findall('onclick')):button.remove(old)
        put(button,'onclick','RunScript(%s,%s,$INFO[Window(Home).Property(MiraPhonePopupPath)])'%(SCRIPTS/'mira_phone_popup.py',action))
    ET.indent(root,space='    ')
    data=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    if b'mira_usb_eject' in data or b'Mira.USB' in data:raise RuntimeError('USB-Aktion im Anruf-Pop-up gefunden.')
    return data

def build_keymap():
    root=ET.Element('keymap');keyboard=ET.SubElement(ET.SubElement(root,'window1190'),'keyboard')
    dismiss='RunScript(%s,dismiss)'%(SCRIPTS/'mira_phone_popup.py')
    actions=dict(one='Down',two='Up',return_='Select',escape=dismiss,backspace=dismiss,
        up='Up',down='Down',left='Left',right='Right',prev_track='Left',next_track='Right')
    for key,value in actions.items():ET.SubElement(keyboard,'return' if key=='return_' else key).text=value
    ET.indent(root,space='    ')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def patch_calls(source):
    if hashlib.sha256(source.encode()).hexdigest()!=CALLS_V10_HASH:
        raise RuntimeError('Anrufskript unterscheidet sich vom erwarteten V10-Stand. Nichts geändert.')
    source=source.replace("filename=W.getProperty('MiraPhoneDataFile') or W.getProperty('MiraPhoneCacheFile')",
        "filename=W.getProperty('MiraPhoneCallContactsFile') or W.getProperty('MiraPhoneDataFile') or W.getProperty('MiraPhoneCacheFile')",1)
    old="def focus(cid):\n    xbmc.executebuiltin('SetFocus(%d)'%cid)"
    new="""def focus(cid):
    if xbmcgui.getCurrentWindowId()==11189 and xbmcgui.getCurrentWindowDialogId()==9999:
        xbmc.executebuiltin('SetFocus(%d)'%cid)"""
    if source.count(old)!=1:raise RuntimeError('Fokusfunktion unerwartet.')
    source='# MIRA_PHONE_POPUP_V11\n'+source.replace(old,new,1)
    ast.parse(source);return source

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def reload():
    subprocess.run(['kodi-send','--action=Action(reloadkeymaps)'],check=False)
    subprocess.run(['kodi-send','--action=ReloadSkin()'],check=False)

def start():
    subprocess.run(['kodi-send','--action=RunScript(%s)'%(SCRIPTS/'mira_phone_call_watch.py')],check=False)

def quiet():
    result=subprocess.run(['/usr/bin/python3',str(SCRIPTS/'mira_phone_call_backend.py')],input='{"action":"status"}',capture_output=True,text=True,timeout=25)
    try:status=json.loads(result.stdout)
    except ValueError:status={}
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
                if time.monotonic()>=deadline:raise RuntimeError('Anrufbeobachter konnte nicht angehalten werden. Keine Konfiguration geändert.')
                time.sleep(0.2)
    except Exception:
        if lock is not None:lock.close()
        STOP.unlink(missing_ok=True)
        raise

def install():
    new=[SKIN/'custom_MiraPhoneIncoming.xml',KEYMAP,SCRIPTS/'mira_phone_global.py',SCRIPTS/'mira_phone_popup.py']
    if any(p.exists() for p in new):raise RuntimeError('Ein neues Ziel existiert bereits. Keine Änderung.')
    for file in SKIN.glob('*.xml'):
        try:root=ET.parse(file).getroot()
        except ET.ParseError:continue
        if root.tag=='window' and root.get('id') in ('1190','11190'):
            raise RuntimeError('Fenster-ID 1190 ist bereits belegt: '+file.name)
    legacy=SCRIPTS/'phone_status.py'
    if legacy.exists():
        import re
        for node in ast.walk(ast.parse(legacy.read_text())):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and re.search(r'ActivateWindow\s*\(\s*(?:1189|11189)\b',node.value,re.I):
                raise RuntimeError('phone_status.py enthält bereits eine automatische Telefonumschaltung. Bitte diese Datei auslesen; keine Dateien geändert.')
    if not (SKIN.parent/'media/mira/phone-call-v4.png').is_file():raise RuntimeError('Telefon-Buttontextur fehlt.')
    phone=ET.parse(SKIN/'custom_MiraPhone.xml').getroot()
    if phone.find(".//include[@content='RNSE_GlobalFooter']") is None:raise RuntimeError('Originalfooter fehlt.')
    old_watch=(SCRIPTS/'mira_phone_call_watch.py').read_text()
    if 'from mira_phone_calls import watch, CACHE' not in old_watch:raise RuntimeError('Anrufbeobachter hat einen unerwarteten Stand.')
    auto=HOME/'.kodi/userdata/autoexec.py';auto_source=auto.read_text() if auto.exists() else ''
    ast.parse(auto_source)
    if 'MIRA_PHONE_POPUP_V11' in auto_source:raise RuntimeError('Startaktion bereits vorhanden.')
    auto_source+='\n# MIRA_PHONE_POPUP_V11\nimport xbmc as _mira_phone_xbmc\n_mira_phone_xbmc.executebuiltin('+repr('RunScript(%s)'%(SCRIPTS/'mira_phone_call_watch.py'))+')\n'
    homefile=SKIN/'Home.xml';home_root=ET.parse(homefile).getroot()
    old_onloads=[ET.tostring(n) for n in home_root.findall('onload')]
    ET.SubElement(home_root,'onload').text='RunScript(%s)'%(SCRIPTS/'mira_phone_call_watch.py')
    if [ET.tostring(n) for n in home_root.findall('onload')][:-1]!=old_onloads:raise RuntimeError('Bestehende Startaktionen verändert.')
    ET.indent(home_root,space='    ')
    changes={SCRIPTS/name:code.encode() for name,code in PAYLOAD.items()}
    changes.update({SCRIPTS/'mira_phone_calls.py':patch_calls((SCRIPTS/'mira_phone_calls.py').read_text()).encode(),
        SKIN/'custom_MiraPhoneIncoming.xml':build_popup((SKIN/'custom_MiraUSBEjectConfirm.xml').read_bytes()),
        KEYMAP:build_keymap(),auto:auto_source.encode(),homefile:ET.tostring(home_root,encoding='utf-8',xml_declaration=True)})
    for path,code in changes.items():
        if path.suffix=='.py':ast.parse(code)
        elif path.suffix=='.xml':ET.fromstring(code)
    lock=quiet()
    try:
        folder=BACKUPS/('phone-popup-v11-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        folder.mkdir(parents=True,mode=0o700);records=[]
        for i,(path,code) in enumerate(changes.items()):
            saved=str(i)+'.bak';before=digest(path)
            if before is not None:shutil.copy2(path,folder/saved)
            records.append(dict(path=str(path),before=before,backup=saved,after=hashlib.sha256(code).hexdigest()))
        (folder/'manifest.json').write_text(json.dumps(records,indent=2))
        try:
            for path,code in changes.items():
                path.parent.mkdir(parents=True,exist_ok=True)
                tmp=path.with_suffix('.v11.tmp');tmp.write_bytes(code);tmp.replace(path)
        except Exception:
            for item in records:
                if item['before'] is None:Path(item['path']).unlink(missing_ok=True)
                else:shutil.copy2(folder/item['backup'],item['path'])
            raise
        LATEST.unlink(missing_ok=True);LATEST.symlink_to(folder.name)
    finally:
        STOP.unlink(missing_ok=True);lock.close()
    reload();start()
    print('Globales Anruf-Pop-up V11 installiert. Backup: '+str(folder))
    print('Annehmen: Telefonansicht. Ablehnen: vorherige Ansicht. Return: nur Pop-up ausblenden.')
    print('Die Simulation wird jetzt auch außerhalb des Telefonfensters erkannt. Kein Anruf gestartet.')

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
    finally:STOP.unlink(missing_ok=True);lock.close()
    reload();print('Pop-up V11 zurückgenommen. Vorherige Dateien wiederhergestellt.')

def backup_git():
    repo=HOME/'rpi-automotive-setup'
    def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True)
    if git('branch','--show-current').stdout.strip()!='main':raise RuntimeError('Nicht auf main.')
    git('fetch','origin');git('merge-base','--is-ancestor','origin/main','HEAD')
    mappings=[(SCRIPTS/name,'mira/userdata/scripts/'+name) for name in (*PAYLOAD,'mira_phone_calls.py')]
    mappings += [(SKIN/'custom_MiraPhoneIncoming.xml','mira/skin.estuary.custom/xml/custom_MiraPhoneIncoming.xml'),
        (SKIN/'Home.xml','mira/skin.estuary.custom/xml/Home.xml'),(KEYMAP,'mira/userdata/keymaps/'+KEYMAP.name),
        (HOME/'.kodi/userdata/autoexec.py','mira/userdata/autoexec.py'),
        (Path(__file__).resolve(),'tools/mira_phone_popup_v11.py')]
    paths=[r for s,r in mappings];status=git('status','--porcelain','--',*paths).stdout
    if status.strip():raise RuntimeError('Exportziele haben lokale Änderungen:\n'+status)
    for source,relative in mappings:
        target=repo/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    git('add','--',*paths)
    result=subprocess.run(['git','-C',str(repo),'diff','--cached','--quiet','--',*paths])
    if result.returncode==1:print(git('commit','--only','-m','MIRA: Globales Anruf-Pop-up im USB-Dialogstil','--',*paths).stdout)
    elif result.returncode:raise RuntimeError('Git-Diff fehlgeschlagen.')
    result=git('push','origin','main');print(result.stdout+result.stderr);print('GitHub-Sicherung abgeschlossen.')

if __name__=='__main__':
    try:
        if len(sys.argv)==1:install()
        elif sys.argv[1:]==['--rollback']:rollback()
        elif sys.argv[1:]==['--backup-git']:backup_git()
        else:raise RuntimeError('Optionen: --rollback oder --backup-git')
    except Exception as error:raise SystemExit('Abgebrochen: '+str(error))
