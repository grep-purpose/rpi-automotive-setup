# MIRA_PHONE_REFRESH_V9
import fcntl
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import xbmc
import xbmcgui


def display_signature(data,mode):
    records=data.get(mode,[]) if mode in ('contacts','calls') else []
    value=[mode,records] if records else [mode,data.get('status'),data.get('loaded'),data.get('errors')]
    return json.dumps(value,ensure_ascii=False,sort_keys=True)

def main():
    root=Path.home()/'.cache/mira-phone'
    root.mkdir(parents=True,exist_ok=True,mode=0o700);root.chmod(0o700)
    lock=open(root/'refresh.lock','a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:lock.close();return
    window=xbmcgui.Window(11189);monitor=xbmc.Monitor()
    worker=None;output=None;token='';signature=None;failed=False
    ui=runpy.run_path(str(Path(__file__).with_name('mira_phone_ui.py')))
    shown_mode=window.getProperty('MiraPhoneView')
    shown=display_signature(ui['read_data'](),shown_mode)
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
                # Detach the old temporary result before deleting it.
                window.setProperty('MiraPhoneDataFile',window.getProperty('MiraPhoneCacheFile'))
                stop();token=request;output=root/('session-'+token+'.json');signature=None;failed=False
                command=['/usr/bin/python3',str(Path(__file__).with_name('mira_phone_data.py')),'--output',str(output)]
                if window.getProperty('MiraPhoneRefreshForce')=='true':command.append('--force')
                worker=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            if output is not None:
                if worker is not None and worker.poll() not in (None,0) and not failed:
                    failed=True
                    fd,name=__import__('tempfile').mkstemp(prefix='.error-',dir=root)
                    with os.fdopen(fd,'w') as handle:json.dump(dict(status='error',contacts=[],calls=[],loaded=[],errors={}),handle)
                    os.replace(name,output)
                try:current=(output.stat().st_mtime_ns,output.stat().st_size)
                except OSError:current=None
                if current is not None and current!=signature:
                    try:data=json.loads(output.read_text())
                    except (OSError,ValueError):data=None
                    if data is not None:
                        signature=current
                        # Initial empty loading/error output must not replace a good cache.
                        loaded=data.get('loaded',[])
                        empty_initial=data.get('status')=='loading' and not loaded
                        transient_error=data.get('status')=='error' and bool(window.getProperty('MiraPhoneCacheFile'))
                        if not empty_initial and not transient_error:
                            window.setProperty('MiraPhoneDataFile',str(output))
                            address=data.get('device')
                            if address:
                                from mira_phone_cache import path
                                cached=path(address)
                                if cached.is_file():window.setProperty('MiraPhoneCacheFile',str(cached))
                            else:
                                window.clearProperty('MiraPhoneCacheFile')
                mode=window.getProperty('MiraPhoneView')
                data=ui['read_data']()
                next_shown=display_signature(data,mode)
                if next_shown!=shown:
                    # view() already renders a newly selected view.
                    if mode!=shown_mode:
                        shown=next_shown;shown_mode=mode
                    else:
                        ui['render']();shown=next_shown
            if monitor.waitForAbort(0.2):break
    except Exception:
        xbmc.log('[MIRA Phone] Aktualisierung fehlgeschlagen; keine persoenlichen Daten protokolliert.',xbmc.LOGERROR)
        if xbmc.getCondVisibility('Window.IsActive(1189)'):
            xbmcgui.Dialog().notification('Telefon','Daten konnten nicht aktualisiert werden.')
    finally:
        if window.getProperty('MiraPhoneRefreshToken')==token:
            window.setProperty('MiraPhoneDataFile',window.getProperty('MiraPhoneCacheFile'))
        stop();lock.close()

if __name__=='__main__':main()
