# MIRA_PHONE_POPUP_V11
from pathlib import Path
import fcntl
import json
import re
import time
import xbmc
import xbmcgui
import mira_phone_calls as calls
from mira_phone_cache import path as cache_path

HOME=xbmcgui.Window(10000)
PHONE=xbmcgui.Window(11189)
BASE=Path(__file__).parent
ROOT=Path.home()/'.cache/mira-phone'
STOP=ROOT/'popup-v11.stop'
DIALOG=1190

def visible():
    return xbmc.getCondVisibility('Window.IsVisible(1190)')

def close():
    if visible():xbmc.executebuiltin('Dialog.Close(1190)')

def contact_file(call):
    match=re.search(r'/dev_([0-9A-Fa-f_]{17})(?:/|$)',call.get('path',''))
    if match:
        return str(cache_path(match[1].replace('_',':')))
    # Test calls contain no telephone number and use a fixed synthetic name.
    return ''

def display(call):
    number=call.get('number','')
    name=calls.find_name(number)
    remote=call.get('name','').strip()
    if number and calls.number_key(remote)==calls.number_key(number):remote=''
    name=name or remote or number or 'Unbekannte Nummer'
    detail=number if number and calls.number_key(name)!=calls.number_key(number) else ''
    return name,detail

class PopupState:
    def __init__(self):
        self.path=''
        self.requested=0
        self.errors=0
    def apply(self,data):
        if not data.get('ok'):
            self.errors+=1
            if self.errors>=3:close()
            return
        self.errors=0
        incoming=next((c for c in data.get('calls',[]) if c.get('state')=='incoming'),None)
        if incoming is None:
            close()
            self.path='';self.requested=0
            HOME.clearProperty('MiraPhonePopupSuppressed')
            return
        path=incoming['path']
        if self.path!=path:
            close();self.path=path;self.requested=0
        if HOME.getProperty('MiraPhonePopupSuppressed')==path:
            close();return
        name,detail=display(incoming)
        HOME.setProperty('MiraPhonePopupName',name)
        HOME.setProperty('MiraPhonePopupDetail',detail)
        HOME.setProperty('MiraPhonePopupPath',path)
        if not visible() and time.monotonic()-self.requested>2:
            self.requested=time.monotonic()
            xbmc.executebuiltin('ActivateWindow(1190)')

def main():
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (ROOT/'call-watch.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        if STOP.exists():return
        monitor=xbmc.Monitor();started={};state=PopupState()
        HOME.clearProperty('MiraPhonePopupSuppressed')
        HOME.setProperty('MiraPhoneGlobalRunning','true')
        try:
            while not monitor.abortRequested() and not STOP.exists():
                data=calls.backend({'action':'status'})
                if data.get('ok'):
                    entries=data.get('calls',[])
                    selected=next((c for c in entries if c.get('path')==PHONE.getProperty('MiraPhoneCallPath')),entries[0] if entries else {})
                    PHONE.setProperty('MiraPhoneCallContactsFile',contact_file(selected))
                calls.update(data,started)
                # Popup caller information can differ from an already active call.
                incoming=next((c for c in data.get('calls',[]) if c.get('state')=='incoming'),None)
                if incoming:
                    PHONE.setProperty('MiraPhoneCallContactsFile',contact_file(incoming))
                state.apply(data)
                if monitor.waitForAbort(0.6 if data.get('calls') else 1):break
        except Exception:
            xbmc.log('[MIRA Phone] Globale Anrufanzeige beendet; keine Anrufdaten protokolliert.',xbmc.LOGERROR)
        finally:
            close()
            HOME.clearProperty('MiraPhoneGlobalRunning')

if __name__=='__main__':main()
