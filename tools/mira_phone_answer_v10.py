#!/usr/bin/env python3
"""MIRA V10: eingehende Anrufe annehmen und deutsche Rufnummern zuordnen."""
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
SCRIPTS=HOME/'.kodi/userdata/scripts'
XML=HOME/'.kodi/addons/skin.estuary.custom/xml/custom_MiraPhone.xml'
BACKUPS=HOME/'.kodi/userdata/mira-backups'
LATEST=BACKUPS/'phone-answer-v10-latest'
CALLS="# MIRA_PHONE_CALL_V10\n# MIRA_PHONE_CALL_V7\nfrom pathlib import Path\nimport datetime\nimport fcntl\nimport json\nimport subprocess\nimport sys\nimport time\nimport xbmc\nimport xbmcgui\n\nW=xbmcgui.Window(11189)\nBASE=Path(__file__).parent\nCACHE=Path.home()/'.cache/mira-phone'\nCACHE.mkdir(parents=True,exist_ok=True,mode=0o700)\n\ndef backend(request):\n    try:\n        result=subprocess.run(['/usr/bin/python3',str(BASE/'mira_phone_call_backend.py')],\n            input=json.dumps(request),capture_output=True,text=True,timeout=25)\n        return json.loads(result.stdout)\n    except Exception:\n        return {'ok':False,'error':'Telefonverbindung antwortet nicht.'}\n\ndef focus(cid):\n    xbmc.executebuiltin('SetFocus(%d)'%cid)\n\ndef number_key(value):\n    value=str(value or '').strip()\n    if value.lower().startswith('tel:'):value=value[4:]\n    value=value.split(';',1)[0]\n    digits=''.join(c for c in value if c in '0123456789')\n    if not digits:return ''\n    if value.startswith('+'):return '+'+digits\n    if digits.startswith('00'):return '+'+digits[2:]\n    if digits.startswith('0'):return '+49'+digits[1:]\n    return digits\n\ndef find_name(number):\n    key=number_key(number)\n    if not key:return ''\n    try:\n        filename=W.getProperty('MiraPhoneDataFile') or W.getProperty('MiraPhoneCacheFile')\n        data=json.loads(Path(filename).read_text())\n        matches=[r for r in data.get('contacts',[])\n                 if any(number_key(n.get('number',''))==key for n in r.get('numbers',[]))]\n        if len(matches)!=1:return ''\n        name=matches[0].get('name','').strip()\n        return name if name and number_key(name)!=key else ''\n    except Exception:return ''\n\ndef update(data,started):\n    if not data.get('ok'):\n        W.setProperty('MiraPhoneCallStatus',data.get('error','Telefon nicht verfügbar'))\n        return\n    entries=data.get('calls',[])\n    previous=W.getProperty('MiraPhoneCallPath')\n    if not entries:\n        if previous:\n            W.setProperty('MiraPhoneCallPresent','')\n            W.setProperty('MiraPhoneCallPath','')\n            if any(xbmc.getCondVisibility('Control.HasFocus(%d)'%c) for c in (9651,9652,9653)):focus(9600)\n        W.setProperty('MiraPhoneCallCanAnswer','')\n        W.setProperty('MiraPhoneCallDetail','')\n        W.setProperty('MiraPhoneCallStatus','')\n        return\n    # Preserve the shown call when several calls exist; never use HangupAll.\n    call=next((c for c in entries if c['path']==previous),entries[0])\n    path=call['path'];state=call['state']\n    number=call['number']\n    remote=call.get('name','').strip()\n    if remote and number_key(remote)==number_key(number):remote=''\n    name=find_name(number) or remote or number or 'Unbekannte Nummer'\n    W.setProperty('MiraPhoneCallName',name)\n    detail=number if number and number_key(name)!=number_key(number) else ''\n    W.setProperty('MiraPhoneCallDetail',detail)\n    W.setProperty('MiraPhoneCallCanAnswer','true' if state=='incoming' else '')\n    W.setProperty('MiraPhoneCallNumber',number)\n    status={'dialing':'Verbindung wird aufgebaut …','alerting':'Es klingelt …',\n        'active':'Im Gespräch','held':'Anruf gehalten','incoming':'Eingehender Anruf',\n        'waiting':'Anklopfender Anruf'}.get(state,'Anruf')\n    duration=''\n    if state=='active':\n        seconds=None\n        if call.get('start'):\n            try:\n                start=datetime.datetime.fromisoformat(call['start'].replace('Z','+00:00'))\n                now=datetime.datetime.now(start.tzinfo)\n                seconds=max(0,int((now-start).total_seconds()))\n            except ValueError:pass\n        if seconds is None:\n            started.setdefault(path,time.monotonic())\n            seconds=int(time.monotonic()-started[path])\n        duration='%02d:%02d'%(seconds//60,seconds%60)\n    W.setProperty('MiraPhoneCallStatus',status)\n    W.setProperty('MiraPhoneCallDuration',duration)\n    W.setProperty('MiraPhoneHangupLabel','Ablehnen' if state in ('incoming','waiting') else 'Auflegen')\n    was_pad=any(xbmc.getCondVisibility('Control.HasFocus(%d)'%cid) for cid in range(9600,9613))\n    W.setProperty('MiraPhoneCallPath',path)\n    W.setProperty('MiraPhoneCallPresent','true')\n    if state=='incoming':\n        if (not previous and was_pad) or xbmc.getCondVisibility('Control.HasFocus(9651)'):focus(9652)\n    elif (not previous and was_pad) or any(xbmc.getCondVisibility('Control.HasFocus(%d)'%c) for c in (9652,9653)):\n        focus(9651)\n\ndef watch():\n    monitor=xbmc.Monitor();started={}\n    while not monitor.abortRequested() and xbmc.getCondVisibility('Window.IsActive(1189)'):\n        update(backend({'action':'status'}),started)\n        if monitor.waitForAbort(1):break\n\ndef main():\n    mode=sys.argv[1] if len(sys.argv)>1 else 'watch'\n    lock=CACHE/('call-watch.lock' if mode=='watch' else 'call-action.lock')\n    with lock.open('a') as handle:\n        try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)\n        except BlockingIOError:return\n        if mode=='watch':watch();return\n        if mode not in ('dial','hangup','answer'):return\n        request={'action':mode}\n        if mode=='dial':request['number']=W.getProperty('MiraPhoneNumber')\n        else:request['path']=W.getProperty('MiraPhoneCallPath')\n        result=backend(request)\n        if not result.get('ok'):\n            xbmcgui.Dialog().ok('Telefon',result.get('error','Telefonaktion fehlgeschlagen.'))\n        # The watch script uses a different path and stays independent of actions.\n        xbmc.executebuiltin('RunScript(%s)'%(BASE/'mira_phone_call_watch.py'))\n\nif __name__=='__main__':main()\n"
SIMULATION="    if simulated:\n        values=json.loads(simfile.read_text())\n        state=values.get('state','incoming')\n        if action=='status':\n            return {'ok':True,'calls':[{'path':simpath,'state':state,\n                'number':'','name':'MIRA Testanruf · Simulation',\n                'start':values.get('start','')}]}\n        if action=='answer':\n            if request.get('path')!=simpath or state!='incoming':\n                raise ValueError('Der simulierte Anruf klingelt nicht mehr.')\n            from datetime import datetime\n            values['state']='active'\n            values['start']=datetime.now().astimezone().isoformat()\n            temporary=simfile.with_suffix('.tmp')\n            fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)\n            with os.fdopen(fd,'w') as output:json.dump(values,output)\n            os.replace(temporary,simfile)\n            return {'ok':True}\n        raise ValueError('Simulation aktiv. Bitte zuerst den Testanruf beenden.')\n"
ANSWER="    if action=='answer':\n        target=request.get('path','')\n        matching=[v for p,v in entries if p==target]\n        if not matching or str(matching[0].get('State',''))!='incoming':\n            raise ValueError('Dieser Anruf klingelt nicht mehr. Nichts angenommen.')\n        dbus.Interface(bus.get_object('org.ofono',target),\n                       'org.ofono.VoiceCall').Answer(timeout=10)\n        return {'ok':True}\n"
BASE_CALLS_HASH='be07816f0d4250898ffc287b788bb54e6d0eb9a72e5798302aaf259d56fa14ac'
def replace_function(source,name,replacement):
    node=next((n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name),None)
    if node is None:raise RuntimeError('Funktion fehlt: '+name)
    lines=source.splitlines(keepends=True)
    return ''.join(lines[:node.lineno-1])+replacement.rstrip()+'\n'+''.join(lines[node.end_lineno:])

def patch_backend(source):
    if 'MIRA_PHONE_SIM_V8' not in source or 'MIRA_PHONE_CALL_V10' in source:
        raise RuntimeError('Erwarteter Simulationsstand V8 fehlt oder V10 ist bereits installiert.')
    fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='execute')
    simulated=[n for n in fn.body if isinstance(n,ast.If) and isinstance(n.test,ast.Name) and n.test.id=='simulated']
    dial=[n for n in fn.body if isinstance(n,ast.If) and isinstance(n.test,ast.Compare) and isinstance(n.test.left,ast.Name) and n.test.left.id=='action' and any(isinstance(c,ast.Constant) and c.value=='dial' for c in n.test.comparators)]
    if len(simulated)!=1 or len(dial)!=1:raise RuntimeError('Backend-Aufbau unerwartet.')
    lines=source.splitlines(keepends=True)
    edits=[(simulated[0].lineno-1,simulated[0].end_lineno,SIMULATION),
           (dial[0].lineno-1,dial[0].lineno-1,ANSWER)]
    for start,end,text in sorted(edits,reverse=True):lines[start:end]=[text.rstrip()+'\n']
    result='# MIRA_PHONE_CALL_V10\n'+''.join(lines)
    ast.parse(result)
    return result

def patch_ui(source):
    if 'MIRA_PHONE_UI_CACHE_V9' not in source or 'MIRA_PHONE_UI_V10' in source:
        raise RuntimeError('Erwarteter UI-Stand mit Cache V9 fehlt oder V10 ist bereits installiert.')
    replacement="""def right():
    if W.getProperty('MiraPhoneCallPresent'):
        return 9652 if W.getProperty('MiraPhoneCallCanAnswer') else 9651
    return 9650 if W.getProperty('MiraPhoneView')=='sms' else 9600
"""
    result='# MIRA_PHONE_UI_V10\n'+replace_function(source,'right',replacement)
    ast.parse(result);return result

def put(node,key,value):
    child=node.find(key)
    if child is None:child=ET.SubElement(node,key)
    child.text=str(value);return child

def patch_xml(source):
    root=ET.fromstring(source)
    footer=root.find(".//include[@content='RNSE_GlobalFooter']")
    if footer is None:raise RuntimeError('Originalfooter fehlt.')
    old_footer=ET.tostring(footer)
    hangup=root.find(".//control[@id='9651']")
    if hangup is None or any(root.find(".//control[@id='%s']"%cid) is not None for cid in (9652,9653)):
        raise RuntimeError('Gesprächsbereich hat einen unerwarteten Stand.')
    group=next(n for n in root.iter() if hangup in list(n))
    detail=[n for n in group.iter('control') if n.findtext('label')=='$INFO[Window(11189).Property(MiraPhoneCallNumber)]']
    if len(detail)!=1:raise RuntimeError('Zweite Nummernzeile nicht eindeutig.')
    put(detail[0],'label','$INFO[Window(11189).Property(MiraPhoneCallDetail)]')
    condition='String.IsEqual(Window(11189).Property(MiraPhoneCallCanAnswer),true)'
    put(hangup,'visible','!'+condition)
    for cid,x,label,action,normal,focused in (
        (9652,1070,'Annehmen','answer','FF10CE50','FF56F080'),
        (9653,1440,'Ablehnen','hangup','FFCE3038','FFFF5050')):
        button=ET.SubElement(group,'control',{'type':'button','id':str(cid)})
        for key,value in dict(left=x,top=910,width=350,height=90,font='font50',
            label='[B]'+label+'[/B]',align='center',aligny='center',
            textcolor='FFFFFFFF',focusedcolor='FF10151C',visible=condition,
            onup=9653 if cid==9652 else 9652,ondown=9653 if cid==9652 else 9652,
            onleft=cid,onright=cid,
            onclick='RunScript(%s,%s)'%(SCRIPTS/'mira_phone_calls.py',action)).items():put(button,key,value)
        for key,color in (('texturefocus',focused),('texturenofocus',normal)):
            put(button,key,'mira/phone-call-v4.png').set('colordiffuse',color)
    if ET.tostring(footer)!=old_footer:raise RuntimeError('Footerprüfung fehlgeschlagen.')
    ids=[n.get('id') for n in root.iter('control') if n.get('id')]
    if len(ids)!=len(set(ids)):raise RuntimeError('Doppelte Control-ID.')
    ET.indent(root,space='    ')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def reload():subprocess.run(['kodi-send','--action=ReloadSkin()'],check=False)

def quiet():
    result=subprocess.run(['/usr/bin/python3',str(SCRIPTS/'mira_phone_call_backend.py')],
        input='{"action":"status"}',text=True,capture_output=True,timeout=25)
    try:status=json.loads(result.stdout)
    except ValueError:status={}
    if status.get('calls'):raise RuntimeError('Bitte den laufenden Anruf bzw. die Simulation zuerst beenden.')
    subprocess.run(['kodi-send','--action=ActivateWindow(Home)'],check=True,capture_output=True)
    folder=HOME/'.cache/mira-phone';folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    handle=(folder/'call-watch.lock').open('a')
    deadline=time.monotonic()+30
    while True:
        try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB);return handle
        except BlockingIOError:
            if time.monotonic()>=deadline:
                handle.close();raise RuntimeError('Alter Anrufbeobachter läuft noch. Nichts geändert.')
            time.sleep(0.2)

def install():
    backend=SCRIPTS/'mira_phone_call_backend.py';calls=SCRIPTS/'mira_phone_calls.py';ui=SCRIPTS/'mira_phone_ui.py'
    if digest(calls)!=BASE_CALLS_HASH:raise RuntimeError('Anrufskript unterscheidet sich vom erwarteten V7-Stand. Nichts geändert.')
    changes={backend:patch_backend(backend.read_text()).encode(),calls:CALLS.encode(),
        ui:patch_ui(ui.read_text()).encode(),XML:patch_xml(XML.read_bytes())}
    for path,code in changes.items():
        if path.suffix=='.py':ast.parse(code)
    lock=quiet()
    try:
        folder=BACKUPS/('phone-answer-v10-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        folder.mkdir(parents=True,mode=0o700);records=[]
        for i,(path,code) in enumerate(changes.items()):
            saved=str(i)+'.bak';shutil.copy2(path,folder/saved)
            records.append(dict(path=str(path),backup=saved,after=hashlib.sha256(code).hexdigest()))
        (folder/'manifest.json').write_text(json.dumps(records,indent=2))
        try:
            for path,code in changes.items():
                temporary=path.with_suffix('.v10.tmp');temporary.write_bytes(code);temporary.replace(path)
        except Exception:
            for item in records:shutil.copy2(folder/item['backup'],item['path'])
            raise
        LATEST.unlink(missing_ok=True);LATEST.symlink_to(folder.name)
    finally:lock.close()
    reload();print('V10 installiert: Annehmen, Kontaktzuordnung und eindeutige Nummernanzeige.')
    print('Backup: '+str(folder));print('Telefonfenster bitte wieder öffnen. Es wurde kein Anruf gestartet oder angenommen.')

def rollback():
    folder=LATEST.resolve(strict=True);records=json.loads((folder/'manifest.json').read_text())
    for item in records:
        if digest(Path(item['path']))!=item['after']:raise RuntimeError('Datei inzwischen geändert: '+item['path'])
    lock=quiet()
    try:
        for item in records:shutil.copy2(folder/item['backup'],item['path'])
    finally:lock.close()
    reload();print('V10 zurückgenommen.')

def backup_git():
    repo=HOME/'rpi-automotive-setup'
    def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True)
    if git('branch','--show-current').stdout.strip()!='main':raise RuntimeError('Nicht auf main.')
    git('fetch','origin');git('merge-base','--is-ancestor','origin/main','HEAD')
    mappings=[(SCRIPTS/name,'mira/userdata/scripts/'+name) for name in ('mira_phone_calls.py','mira_phone_call_backend.py','mira_phone_ui.py')]
    mappings += [(XML,'mira/skin.estuary.custom/xml/custom_MiraPhone.xml'),(Path(__file__).resolve(),'tools/mira_phone_answer_v10.py')]
    paths=[r for s,r in mappings]
    status=git('status','--porcelain','--',*paths).stdout
    if status.strip():raise RuntimeError('Exportziele haben lokale Änderungen:\n'+status)
    for source,relative in mappings:
        target=repo/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    git('add','--',*paths)
    result=subprocess.run(['git','-C',str(repo),'diff','--cached','--quiet','--',*paths])
    if result.returncode==1:print(git('commit','--only','-m','MIRA: Anrufe annehmen und Kontaktnamen zuordnen','--',*paths).stdout)
    elif result.returncode:raise RuntimeError('Git-Diff fehlgeschlagen.')
    result=git('push','origin','main');print(result.stdout+result.stderr);print('GitHub-Sicherung abgeschlossen.')

if __name__=='__main__':
    try:
        if len(sys.argv)==1:install()
        elif sys.argv[1:]==['--rollback']:rollback()
        elif sys.argv[1:]==['--backup-git']:backup_git()
        else:raise RuntimeError('Optionen: --rollback oder --backup-git')
    except Exception as error:raise SystemExit('Abgebrochen: '+str(error))
