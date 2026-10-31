# MIRA_PHONE_POPUP_V11
from pathlib import Path
import fcntl
import sys
import xbmc
import xbmcgui
from mira_phone_calls import backend

HOME=xbmcgui.Window(10000)
ROOT=Path.home()/'.cache/mira-phone'
BASE=Path(__file__).parent

def close():xbmc.executebuiltin('Dialog.Close(1190)')

def main():
    action=sys.argv[1] if len(sys.argv)>1 else 'dismiss'
    path=sys.argv[2] if len(sys.argv)>2 else HOME.getProperty('MiraPhonePopupPath')
    if action in ('dismiss','closed'):
        if path:HOME.setProperty('MiraPhonePopupSuppressed',path)
        if action=='dismiss':close()
        return
    if action not in ('answer','hangup') or not path:return
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (ROOT/'call-action.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        # The path is frozen in the button action; the backend rechecks it.
        result=backend({'action':action,'path':path})
        if not result.get('ok'):
            xbmcgui.Dialog().notification('Telefon',result.get('error','Telefonaktion fehlgeschlagen.'))
            return
        HOME.setProperty('MiraPhonePopupSuppressed',path)
        close()
        if action=='answer':
            phone=xbmcgui.Window(11189)
            was_phone=xbmcgui.getCurrentWindowId()==11189
            old_token=phone.getProperty('MiraPhoneRefreshToken')
            xbmc.executebuiltin('ActivateWindow(1189)')
            monitor=xbmc.Monitor()
            for _ in range(50):
                ready=was_phone or phone.getProperty('MiraPhoneRefreshToken')!=old_token
                if (ready and xbmcgui.getCurrentWindowId()==11189
                        and xbmcgui.getCurrentWindowDialogId()==9999
                        and phone.getProperty('MiraPhoneCallPresent')
                        and not phone.getProperty('MiraPhoneCallCanAnswer')):
                    xbmc.executebuiltin('SetFocus(9651)')
                    return
                if monitor.waitForAbort(0.1):return

if __name__=='__main__':main()
