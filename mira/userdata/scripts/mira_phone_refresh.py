# MIRA_PHONE_REFRESH_V5
import fcntl
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import time
import xbmc
import xbmcgui


def main():
    root=Path.home()/'.cache/mira-phone';root.mkdir(parents=True,exist_ok=True,mode=0o700);root.chmod(0o700)
    lock=open(root/'refresh.lock','a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:lock.close();return
    window=xbmcgui.Window(11189);monitor=xbmc.Monitor();worker=None;output=None;token='';signature=None;last_mode='';failed=False
    ui=runpy.run_path(str(Path(__file__).with_name('mira_phone_ui.py')))
    def stop():
        nonlocal worker,output
        if worker is not None and worker.poll() is None:
            worker.terminate()
            try:worker.wait(timeout=3)
            except subprocess.TimeoutExpired:worker.kill();worker.wait(timeout=3)
        worker=None
        if output is not None:
            output.unlink(missing_ok=True)
            for folder in root.glob('mira-pbap-'+output.stem+'-*'):
                if folder.is_dir():shutil.rmtree(folder)
        output=None
    try:
        while not monitor.abortRequested() and xbmc.getCondVisibility('Window.IsActive(1189)'):
            request=window.getProperty('MiraPhoneRefreshToken')
            if request!=token and re.fullmatch('[a-f0-9]{32}',request or ''):
                stop();token=request;output=root/('session-'+token+'.json');signature=None;failed=False
                window.setProperty('MiraPhoneDataFile',str(output))
                worker=subprocess.Popen(['/usr/bin/python3',str(Path(__file__).with_name('mira_phone_data.py')),'--output',str(output)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            if output is not None:
                if worker is not None and worker.poll() not in (None,0) and not failed:
                    failed=True
                    fd,name=__import__('tempfile').mkstemp(prefix='.error-',dir=root)
                    with os.fdopen(fd,'w') as handle:json.dump(dict(status='error',contacts=[],calls=[],loaded=[],errors={}),handle)
                    os.replace(name,output)
                try:current=(output.stat().st_mtime_ns,output.stat().st_size)
                except OSError:current=None
                mode=window.getProperty('MiraPhoneView')
                if current!=signature or mode!=last_mode:
                    ui['render']();signature=current;last_mode=mode
            if monitor.waitForAbort(0.15):break
    except Exception:
        xbmc.log('[MIRA Phone] Aktualisierung fehlgeschlagen; keine persoenlichen Daten protokolliert.',xbmc.LOGERROR)
        if xbmc.getCondVisibility('Window.IsActive(1189)'):
            xbmcgui.Dialog().notification('Telefon','Daten konnten nicht geladen werden.')
    finally:
        stop()
        if window.getProperty('MiraPhoneRefreshToken')==token:window.clearProperty('MiraPhoneDataFile')
        lock.close()

if __name__=='__main__':main()
