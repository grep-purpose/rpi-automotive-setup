# MIRA_PHONE_CALL_V10
# MIRA_PHONE_CALL_V7
from pathlib import Path
import datetime
import fcntl
import json
import subprocess
import sys
import time
import xbmc
import xbmcgui

W=xbmcgui.Window(11189)
BASE=Path(__file__).parent
CACHE=Path.home()/'.cache/mira-phone'
CACHE.mkdir(parents=True,exist_ok=True,mode=0o700)

def backend(request):
    try:
        result=subprocess.run(['/usr/bin/python3',str(BASE/'mira_phone_call_backend.py')],
            input=json.dumps(request),capture_output=True,text=True,timeout=25)
        return json.loads(result.stdout)
    except Exception:
        return {'ok':False,'error':'Telefonverbindung antwortet nicht.'}

def focus(cid):
    xbmc.executebuiltin('SetFocus(%d)'%cid)

def number_key(value):
    value=str(value or '').strip()
    if value.lower().startswith('tel:'):value=value[4:]
    value=value.split(';',1)[0]
    digits=''.join(c for c in value if c in '0123456789')
    if not digits:return ''
    if value.startswith('+'):return '+'+digits
    if digits.startswith('00'):return '+'+digits[2:]
    if digits.startswith('0'):return '+49'+digits[1:]
    return digits

def find_name(number):
    key=number_key(number)
    if not key:return ''
    try:
        filename=W.getProperty('MiraPhoneDataFile') or W.getProperty('MiraPhoneCacheFile')
        data=json.loads(Path(filename).read_text())
        matches=[r for r in data.get('contacts',[])
                 if any(number_key(n.get('number',''))==key for n in r.get('numbers',[]))]
        if len(matches)!=1:return ''
        name=matches[0].get('name','').strip()
        return name if name and number_key(name)!=key else ''
    except Exception:return ''

def update(data,started):
    if not data.get('ok'):
        W.setProperty('MiraPhoneCallStatus',data.get('error','Telefon nicht verfügbar'))
        return
    entries=data.get('calls',[])
    previous=W.getProperty('MiraPhoneCallPath')
    if not entries:
        if previous:
            W.setProperty('MiraPhoneCallPresent','')
            W.setProperty('MiraPhoneCallPath','')
            if any(xbmc.getCondVisibility('Control.HasFocus(%d)'%c) for c in (9651,9652,9653)):focus(9600)
        W.setProperty('MiraPhoneCallCanAnswer','')
        W.setProperty('MiraPhoneCallDetail','')
        W.setProperty('MiraPhoneCallStatus','')
        return
    # Preserve the shown call when several calls exist; never use HangupAll.
    call=next((c for c in entries if c['path']==previous),entries[0])
    path=call['path'];state=call['state']
    number=call['number']
    remote=call.get('name','').strip()
    if remote and number_key(remote)==number_key(number):remote=''
    name=find_name(number) or remote or number or 'Unbekannte Nummer'
    W.setProperty('MiraPhoneCallName',name)
    detail=number if number and number_key(name)!=number_key(number) else ''
    W.setProperty('MiraPhoneCallDetail',detail)
    W.setProperty('MiraPhoneCallCanAnswer','true' if state=='incoming' else '')
    W.setProperty('MiraPhoneCallNumber',number)
    status={'dialing':'Verbindung wird aufgebaut …','alerting':'Es klingelt …',
        'active':'Im Gespräch','held':'Anruf gehalten','incoming':'Eingehender Anruf',
        'waiting':'Anklopfender Anruf'}.get(state,'Anruf')
    duration=''
    if state=='active':
        seconds=None
        if call.get('start'):
            try:
                start=datetime.datetime.fromisoformat(call['start'].replace('Z','+00:00'))
                now=datetime.datetime.now(start.tzinfo)
                seconds=max(0,int((now-start).total_seconds()))
            except ValueError:pass
        if seconds is None:
            started.setdefault(path,time.monotonic())
            seconds=int(time.monotonic()-started[path])
        duration='%02d:%02d'%(seconds//60,seconds%60)
    W.setProperty('MiraPhoneCallStatus',status)
    W.setProperty('MiraPhoneCallDuration',duration)
    W.setProperty('MiraPhoneHangupLabel','Ablehnen' if state in ('incoming','waiting') else 'Auflegen')
    was_pad=any(xbmc.getCondVisibility('Control.HasFocus(%d)'%cid) for cid in range(9600,9613))
    W.setProperty('MiraPhoneCallPath',path)
    W.setProperty('MiraPhoneCallPresent','true')
    if state=='incoming':
        if (not previous and was_pad) or xbmc.getCondVisibility('Control.HasFocus(9651)'):focus(9652)
    elif (not previous and was_pad) or any(xbmc.getCondVisibility('Control.HasFocus(%d)'%c) for c in (9652,9653)):
        focus(9651)

def watch():
    monitor=xbmc.Monitor();started={}
    while not monitor.abortRequested() and xbmc.getCondVisibility('Window.IsActive(1189)'):
        update(backend({'action':'status'}),started)
        if monitor.waitForAbort(1):break

def main():
    mode=sys.argv[1] if len(sys.argv)>1 else 'watch'
    lock=CACHE/('call-watch.lock' if mode=='watch' else 'call-action.lock')
    with lock.open('a') as handle:
        try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        if mode=='watch':watch();return
        if mode not in ('dial','hangup','answer'):return
        request={'action':mode}
        if mode=='dial':request['number']=W.getProperty('MiraPhoneNumber')
        else:request['path']=W.getProperty('MiraPhoneCallPath')
        result=backend(request)
        if not result.get('ok'):
            xbmcgui.Dialog().ok('Telefon',result.get('error','Telefonaktion fehlgeschlagen.'))
        # The watch script uses a different path and stays independent of actions.
        xbmc.executebuiltin('RunScript(%s)'%(BASE/'mira_phone_call_watch.py'))

if __name__=='__main__':main()
