#!/usr/bin/env python3
"""MIRA Telefon V9: gerätegebundener Cache und Aktualisierung im Hintergrund."""
from pathlib import Path
from datetime import datetime
import ast
import hashlib
import json
import shutil
import subprocess
import sys
HOME=Path.home()
SCRIPTS=HOME/'.kodi/userdata/scripts'
BACKUPS=HOME/'.kodi/userdata/mira-backups'
LATEST=BACKUPS/'phone-cache-v9-latest'
PAYLOAD={'mira_phone_cache.py': "# MIRA_PHONE_CACHE_V9\nfrom pathlib import Path\nimport hashlib\nimport json\nimport os\nimport tempfile\nimport time\n\nROOT=Path.home()/'.cache/mira-phone'\n\ndef device():\n    import dbus\n    bus=dbus.SystemBus()\n    objects=dbus.Interface(bus.get_object('org.bluez','/'),\n        'org.freedesktop.DBus.ObjectManager').GetManagedObjects(timeout=3)\n    found=[]\n    for interfaces in objects.values():\n        props=interfaces.get('org.bluez.Device1',{})\n        if props.get('Connected',False) and '0000112f-0000-1000-8000-00805f9b34fb' in [str(x).lower() for x in props.get('UUIDs',[])]:\n            found.append(str(props['Address']).upper())\n    return found\n\ndef path(address):\n    return ROOT/('cache-v9-'+hashlib.sha256(address.upper().encode()).hexdigest()+'.json')\n\ndef load(address):\n    try:\n        data=json.loads(path(address).read_text())\n        if data.get('device')!=address.upper():return None\n        if not isinstance(data.get('contacts'),list) or not isinstance(data.get('calls'),list):return None\n        if not isinstance(data.get('_cached_at'),dict):return None\n        return data\n    except (OSError,ValueError,AttributeError):return None\n\ndef save(data):\n    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700);ROOT.chmod(0o700)\n    content=dict(data,status='complete',errors={})\n    fd,name=tempfile.mkstemp(prefix='.cache-',dir=ROOT)\n    try:\n        with os.fdopen(fd,'w') as output:json.dump(content,output,ensure_ascii=False)\n        os.replace(name,path(data['device']))\n    finally:Path(name).unlink(missing_ok=True)\n\ndef probe():\n    found=device()\n    if len(found)==1 and load(found[0]) is not None:\n        return str(path(found[0]))\n    return ''\n\nif __name__=='__main__':\n    try:print(probe())\n    except Exception:print('')\n", 'mira_phone_data.py': '# MIRA_PHONE_DATA_CACHE_V9\n#!/usr/bin/env python3\n"""Read-only PBAP worker. No call, message, read-status or audio mutations."""\nimport argparse\nimport codecs\nfrom datetime import datetime\nimport json\nimport os\nfrom pathlib import Path\nimport quopri\nimport re\nimport tempfile\nimport time\nimport unicodedata\nfrom mira_phone_cache import load as cache_load, save as cache_save\n\n\ndef unescape(value):\n    return re.sub(r\'\\\\([nN,;\\\\])\',lambda m:\'\\n\' if m[1].lower()==\'n\' else m[1],value)\n\n\ndef normalize(value):\n    value=re.sub(r\'^tel:\', \'\', value, flags=re.I).split(\';\',1)[0]\n    return (\'+\' if value.strip().startswith(\'+\') else \'\')+\'\'.join(re.findall(r\'[0-9]\',value))\n\n\ndef initial(name):\n    value=\'\'.join(c for c in unicodedata.normalize(\'NFKD\',name) if not unicodedata.combining(c)).upper()\n    return value[0] if value and \'A\'<=value[0]<=\'Z\' else \'#\'\n\n\ndef parse_cards(text):\n    lines=[]\n    for line in text.replace(\'\\r\\n\',\'\\n\').splitlines():\n        if lines and lines[-1].endswith(\'=\') and \'ENCODING=QUOTED-PRINTABLE\' in lines[-1].upper():\n            lines[-1]=lines[-1][:-1]+line.lstrip()\n        elif line.startswith((\' \',\'\\t\')) and lines:\n            lines[-1]+=line[1:]\n        else: lines.append(line)\n    records=[];current=None\n    for line in lines:\n        if line.upper()==\'BEGIN:VCARD\': current=[]\n        elif line.upper()==\'END:VCARD\':\n            if current is not None: records.append(current)\n            current=None\n        elif current is not None and \':\' in line:\n            head,value=line.split(\':\',1);parts=head.split(\';\');field=parts[0].rsplit(\'.\',1)[-1].upper()\n            params=[p.upper() for p in parts[1:]]\n            if \'ENCODING=QUOTED-PRINTABLE\' in params:\n                charset=next((p.split(\'=\',1)[1] for p in parts[1:] if p.upper().startswith(\'CHARSET=\')),\'utf-8\')\n                try: value=quopri.decodestring(value).decode(charset,errors=\'replace\')\n                except (LookupError,ValueError): value=quopri.decodestring(value).decode(\'utf-8\',errors=\'replace\')\n            current.append((field,params,value))\n    return records\n\n\ndef phone_record(card):\n    def first(key):return next((value for field,params,value in card if field==key),\'\')\n    name=unescape(first(\'FN\')).strip()\n    if not name:\n        parts=re.split(r\'(?<!\\\\);\',first(\'N\'))\n        if len(parts)>1:name=\' \'.join(unescape(x) for x in (parts[1:3]+parts[:1]) if x).strip()\n    numbers=[];seen=set()\n    for field,params,value in card:\n        if field!=\'TEL\':continue\n        raw=unescape(value).strip();number=normalize(raw)\n        if not any(c.isdigit() for c in number) or number in seen:continue\n        seen.add(number);types=\',\'.join(params)\n        label=\'Mobil\' if \'CELL\' in types else \'Privat\' if \'HOME\' in types else \'Arbeit\' if \'WORK\' in types else \'Telefon\'\n        numbers.append(dict(number=number,display=raw,label=label))\n    return dict(name=name or (numbers[0][\'display\'] if numbers else \'Unbekannt\'),numbers=numbers)\n\n\ndef contacts_from(text):\n    result=[phone_record(card) for card in parse_cards(text)]\n    result=[record for record in result if record[\'numbers\']]\n    result.sort(key=lambda r:\'\'.join(c for c in unicodedata.normalize(\'NFKD\',r[\'name\']).casefold() if not unicodedata.combining(c)))\n    for record in result:record[\'initial\']=initial(record[\'name\'])\n    return result\n\n\ndef calls_from(text,contacts):\n    names={}\n    for contact in contacts:\n        for number in contact[\'numbers\']:names.setdefault(number[\'number\'],set()).add(contact[\'name\'])\n    result=[]\n    for card in parse_cards(text):\n        record=phone_record(card)\n        if record[\'numbers\']:\n            number=record[\'numbers\'][0][\'number\'];candidates=names.get(number,set())\n            if len(candidates)==1 and (record[\'name\']==record[\'numbers\'][0][\'display\'] or record[\'name\']==\'Unbekannt\'):\n                record[\'name\']=next(iter(candidates))\n        stamp=\'\';kind=\'Anruf\';sort=\'\'\n        for field,params,value in card:\n            if field!=\'X-IRMC-CALL-DATETIME\':continue\n            flags=\',\'.join(params)\n            kind=\'Verpasst\' if \'MISSED\' in flags else \'Ausgehend\' if \'DIALED\' in flags else \'Eingehend\' if \'RECEIVED\' in flags else \'Anruf\'\n            try:\n                dt=datetime.fromisoformat(value.strip().replace(\'Z\',\'+00:00\'))\n                if dt.tzinfo:dt=dt.astimezone()\n                stamp=dt.strftime(\'%d.%m.%Y %H:%M\');sort=dt.strftime(\'%Y%m%d%H%M%S\')\n            except ValueError:pass\n        record.update(kind=kind,time=stamp,sort=sort)\n        if not record[\'numbers\'] and record[\'name\']==\'Unbekannt\':record[\'name\']=\'Unbekannte Rufnummer\'\n        result.append(record)\n    result.sort(key=lambda r:r[\'sort\'],reverse=True)\n    return result\n\n\ndef main():\n    parser=argparse.ArgumentParser();parser.add_argument(\'--output\',required=True);parser.add_argument(\'--force\',action=\'store_true\');args=parser.parse_args()\n    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)\n    data=dict(status=\'loading\',contacts=[],calls=[],loaded=[],errors={})\n    def publish():\n        fd,name=tempfile.mkstemp(prefix=\'.phone-\',dir=output.parent)\n        try:\n            with os.fdopen(fd,\'w\',encoding=\'utf-8\') as handle:json.dump(data,handle,ensure_ascii=False)\n            os.replace(name,output)\n        finally:Path(name).unlink(missing_ok=True)\n    publish();session=None;client=None\n    try:\n        import dbus\n        from dbus.mainloop.glib import DBusGMainLoop\n        from gi.repository import GLib\n        DBusGMainLoop(set_as_default=True)\n        system=dbus.SystemBus()\n        objects=dbus.Interface(system.get_object(\'org.bluez\',\'/\'),\'org.freedesktop.DBus.ObjectManager\').GetManagedObjects(timeout=15)\n        devices=[]\n        for path,interfaces in objects.items():\n            device=interfaces.get(\'org.bluez.Device1\',{})\n            uuids=[str(x).lower() for x in device.get(\'UUIDs\',[])]\n            if device.get(\'Connected\',False) and \'0000112f-0000-1000-8000-00805f9b34fb\' in uuids:\n                devices.append(str(device[\'Address\']))\n        if len(devices)!=1:\n            data[\'status\']=\'no_device\' if not devices else \'multiple_devices\';publish();return\n        address=devices[0].upper()\n        cached=cache_load(address)\n        if cached is not None:data.update(cached)\n        data[\'device\']=address\n        data.setdefault(\'_cached_at\',{})\n        data[\'status\']=\'loading\';data[\'errors\']={};publish()\n        bus=dbus.SessionBus();states={};context=GLib.MainContext.default()\n        def changed(interface,values,invalidated,path=None):\n            if str(interface)==\'org.bluez.obex.Transfer1\':states.setdefault(str(path),{}).update(dict(values))\n        bus.add_signal_receiver(changed,signal_name=\'PropertiesChanged\',dbus_interface=\'org.freedesktop.DBus.Properties\',bus_name=\'org.bluez.obex\',path_keyword=\'path\')\n        client=dbus.Interface(bus.get_object(\'org.bluez.obex\',\'/org/bluez/obex\'),\'org.bluez.obex.Client1\')\n        session=client.CreateSession(devices[0],dbus.Dictionary({\'Target\':\'pbap\'},signature=\'sv\'),timeout=60)\n        pbap=dbus.Interface(bus.get_object(\'org.bluez.obex\',session),\'org.bluez.obex.PhonebookAccess1\')\n        with tempfile.TemporaryDirectory(prefix=\'mira-pbap-\'+output.stem+\'-\',dir=output.parent) as folder:\n            folder=Path(folder)\n            for book,key in ((\'pb\',\'contacts\'),(\'cch\',\'calls\')):\n                age=time.time()-data[\'_cached_at\'].get(key,0)\n                if key==\'contacts\' and key in data[\'loaded\'] and 0<=age<300 and not args.force:\n                    continue\n                try:\n                    pbap.Select(\'int\',book,timeout=30)\n                    target=folder/(book+\'.vcf\')\n                    path,initial_props=pbap.PullAll(str(target),dbus.Dictionary({\'Format\':\'vcard30\',\'MaxCount\':dbus.UInt16(5000)},signature=\'sv\'),timeout=30)\n                    props=dbus.Interface(bus.get_object(\'org.bluez.obex\',path),\'org.freedesktop.DBus.Properties\')\n                    values=dict(initial_props);deadline=time.monotonic()+90;next_poll=0\n                    while True:\n                        while context.pending():context.iteration(False)\n                        if time.monotonic()>=next_poll:\n                            try:values.update(props.GetAll(\'org.bluez.obex.Transfer1\',timeout=5))\n                            except dbus.DBusException as error:\n                                if error.get_dbus_name()!=\'org.freedesktop.DBus.Error.UnknownObject\':raise\n                            next_poll=time.monotonic()+0.5\n                        values.update(states.get(str(path),{}));status=str(values.get(\'Status\',\'\'))\n                        if status==\'complete\':break\n                        if status==\'error\':raise RuntimeError(\'TransferError\')\n                        if time.monotonic()>deadline:raise TimeoutError(\'TransferTimeout\')\n                        time.sleep(0.05)\n                    actual=Path(str(values.get(\'Filename\',target))).resolve()\n                    if not actual.is_relative_to(folder.resolve()):raise RuntimeError(\'UnexpectedTransferPath\')\n                    text=actual.read_text(encoding=\'utf-8-sig\',errors=\'replace\')\n                    data[key]=contacts_from(text) if key==\'contacts\' else calls_from(text,data[\'contacts\'])\n                    if key not in data[\'loaded\']:data[\'loaded\'].append(key)\n                    data[\'_cached_at\'][key]=time.time()\n                    cache_save(data)\n                except Exception as error:\n                    data[\'errors\'][key]=error.get_dbus_name() if hasattr(error,\'get_dbus_name\') else type(error).__name__\n                publish()\n        data[\'status\']=\'complete\';publish()\n    except Exception as error:\n        data[\'status\']=\'error\';data[\'errors\'][\'connection\']=error.get_dbus_name() if hasattr(error,\'get_dbus_name\') else type(error).__name__;publish()\n    finally:\n        if session is not None and client is not None:\n            try:client.RemoveSession(session,timeout=10)\n            except Exception:pass\n\nif __name__==\'__main__\':main()\n', 'mira_phone_refresh.py': "# MIRA_PHONE_REFRESH_V9\nimport fcntl\nimport json\nimport os\nfrom pathlib import Path\nimport re\nimport runpy\nimport shutil\nimport subprocess\nimport xbmc\nimport xbmcgui\n\n\ndef display_signature(data,mode):\n    records=data.get(mode,[]) if mode in ('contacts','calls') else []\n    value=[mode,records] if records else [mode,data.get('status'),data.get('loaded'),data.get('errors')]\n    return json.dumps(value,ensure_ascii=False,sort_keys=True)\n\ndef main():\n    root=Path.home()/'.cache/mira-phone'\n    root.mkdir(parents=True,exist_ok=True,mode=0o700);root.chmod(0o700)\n    lock=open(root/'refresh.lock','a')\n    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)\n    except BlockingIOError:lock.close();return\n    window=xbmcgui.Window(11189);monitor=xbmc.Monitor()\n    worker=None;output=None;token='';signature=None;failed=False\n    ui=runpy.run_path(str(Path(__file__).with_name('mira_phone_ui.py')))\n    shown_mode=window.getProperty('MiraPhoneView')\n    shown=display_signature(ui['read_data'](),shown_mode)\n    def stop():\n        nonlocal worker,output\n        if worker is not None and worker.poll() is None:\n            worker.terminate()\n            try:worker.wait(timeout=3)\n            except subprocess.TimeoutExpired:worker.kill();worker.wait(timeout=3)\n        worker=None\n        if output is not None:\n            output.unlink(missing_ok=True)\n            for folder in root.glob('mira-pbap-'+output.stem+'-*'):\n                if folder.is_dir():shutil.rmtree(folder)\n        output=None\n    try:\n        while not monitor.abortRequested() and xbmc.getCondVisibility('Window.IsActive(1189)'):\n            request=window.getProperty('MiraPhoneRefreshToken')\n            if request!=token and re.fullmatch('[a-f0-9]{32}',request or ''):\n                # Detach the old temporary result before deleting it.\n                window.setProperty('MiraPhoneDataFile',window.getProperty('MiraPhoneCacheFile'))\n                stop();token=request;output=root/('session-'+token+'.json');signature=None;failed=False\n                command=['/usr/bin/python3',str(Path(__file__).with_name('mira_phone_data.py')),'--output',str(output)]\n                if window.getProperty('MiraPhoneRefreshForce')=='true':command.append('--force')\n                worker=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)\n            if output is not None:\n                if worker is not None and worker.poll() not in (None,0) and not failed:\n                    failed=True\n                    fd,name=__import__('tempfile').mkstemp(prefix='.error-',dir=root)\n                    with os.fdopen(fd,'w') as handle:json.dump(dict(status='error',contacts=[],calls=[],loaded=[],errors={}),handle)\n                    os.replace(name,output)\n                try:current=(output.stat().st_mtime_ns,output.stat().st_size)\n                except OSError:current=None\n                if current is not None and current!=signature:\n                    try:data=json.loads(output.read_text())\n                    except (OSError,ValueError):data=None\n                    if data is not None:\n                        signature=current\n                        # Initial empty loading/error output must not replace a good cache.\n                        loaded=data.get('loaded',[])\n                        empty_initial=data.get('status')=='loading' and not loaded\n                        transient_error=data.get('status')=='error' and bool(window.getProperty('MiraPhoneCacheFile'))\n                        if not empty_initial and not transient_error:\n                            window.setProperty('MiraPhoneDataFile',str(output))\n                            address=data.get('device')\n                            if address:\n                                from mira_phone_cache import path\n                                cached=path(address)\n                                if cached.is_file():window.setProperty('MiraPhoneCacheFile',str(cached))\n                            else:\n                                window.clearProperty('MiraPhoneCacheFile')\n                mode=window.getProperty('MiraPhoneView')\n                data=ui['read_data']()\n                next_shown=display_signature(data,mode)\n                if next_shown!=shown:\n                    # view() already renders a newly selected view.\n                    if mode!=shown_mode:\n                        shown=next_shown;shown_mode=mode\n                    else:\n                        ui['render']();shown=next_shown\n            if monitor.waitForAbort(0.2):break\n    except Exception:\n        xbmc.log('[MIRA Phone] Aktualisierung fehlgeschlagen; keine persoenlichen Daten protokolliert.',xbmc.LOGERROR)\n        if xbmc.getCondVisibility('Window.IsActive(1189)'):\n            xbmcgui.Dialog().notification('Telefon','Daten konnten nicht aktualisiert werden.')\n    finally:\n        if window.getProperty('MiraPhoneRefreshToken')==token:\n            window.setProperty('MiraPhoneDataFile',window.getProperty('MiraPhoneCacheFile'))\n        stop();lock.close()\n\nif __name__=='__main__':main()\n"}

def change_ui(source):
    if '# MIRA_PHONE_SELECT_V6' not in source or '# MIRA_PHONE_CALL_V7' not in source:
        raise RuntimeError('Telefonstand V7 mit Auswahlkorrektur V6 wird erwartet.')
    if '# MIRA_PHONE_UI_CACHE_V9' in source:raise RuntimeError('Cache V9 bereits installiert.')
    def replace(old,new):
        nonlocal source
        if source.count(old)!=1:raise RuntimeError('UI-Skript hat einen unerwarteten Aufbau. Nichts geändert.')
        source=source.replace(old,new,1)
    replace('import json\n','import json\nimport subprocess\n')
    replace('def refresh():','def refresh(force=False):\n    W.setProperty(\'MiraPhoneRefreshForce\',\'true\' if force else \'false\')')
    replace('elif selected==3:refresh()','elif selected==3:refresh(True)')
    replace("W.setProperty('MiraPhoneNumber','');W.setProperty('MiraPhoneDataFile','')", """W.setProperty('MiraPhoneNumber','')
        cached=''
        try:
            probe=subprocess.run(['/usr/bin/python3',str(Path(__file__).with_name('mira_phone_cache.py'))],capture_output=True,text=True,timeout=4)
            candidate=probe.stdout.strip()
            if candidate and Path(candidate).is_file():cached=candidate
        except Exception:pass
        W.setProperty('MiraPhoneDataFile',cached)
        W.setProperty('MiraPhoneCacheFile',cached)""")
    replace("""    try:
        old=control.getSelectedItem()
        if old and W.getProperty('MiraPhoneRenderedView')==mode:old_key=old.getProperty('MiraPhoneKey')
        old_position=control.getSelectedPosition()
    except (RuntimeError,AttributeError):old_position=0""", """    if W.getProperty('MiraPhoneRenderedView')==mode:
        old_key=xbmc.getInfoLabel('Container(50).ListItem.Property(MiraPhoneKey)')
    try:old_position=max(0,int(xbmc.getInfoLabel('Container(50).CurrentItem'))-1)
    except ValueError:old_position=0""")
    source='# MIRA_PHONE_UI_CACHE_V9\n'+source
    ast.parse(source)
    return source

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def reload():subprocess.run(['kodi-send','--action=ReloadSkin()'],check=False)

def install():
    source=change_ui((SCRIPTS/'mira_phone_ui.py').read_text())
    originals={'mira_phone_data.py':b'Read-only PBAP worker', 'mira_phone_refresh.py':b'MIRA_PHONE_REFRESH_V5'}
    for name,marker in originals.items():
        if marker not in (SCRIPTS/name).read_bytes():raise RuntimeError('Erwarteter Stand fehlt: '+name)
    if (SCRIPTS/'mira_phone_cache.py').exists():raise RuntimeError('Cache-Helfer existiert bereits.')
    changes={SCRIPTS/name:code.encode() for name,code in PAYLOAD.items()}
    changes[SCRIPTS/'mira_phone_ui.py']=source.encode()
    for path,code in changes.items():ast.parse(code)
    folder=BACKUPS/('phone-cache-v9-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir(parents=True,mode=0o700)
    records=[]
    for index,(path,code) in enumerate(changes.items()):
        before=digest(path);saved=str(index)+'.bak'
        if before is not None:shutil.copy2(path,folder/saved)
        records.append(dict(path=str(path),before=before,backup=saved,after=hashlib.sha256(code).hexdigest()))
    (folder/'manifest.json').write_text(json.dumps(records,indent=2))
    try:
        for path,code in changes.items():
            temp=path.with_suffix('.v9.tmp');temp.write_bytes(code);temp.replace(path)
    except Exception:
        for item in records:
            path=Path(item['path'])
            if item['before'] is None:path.unlink(missing_ok=True)
            else:shutil.copy2(folder/item['backup'],path)
        raise
    LATEST.unlink(missing_ok=True);LATEST.symlink_to(folder.name)
    reload()
    print('Telefon-Cache V9 installiert. Backup: '+str(folder))
    print('Beim ersten Öffnen wird der Cache aufgebaut. Danach werden vorhandene Daten sofort angezeigt.')
    print('Anrufliste: Aktualisierung bei jedem Öffnen. Kontakte: spätestens nach 5 Minuten beim Öffnen.')
    print('Daten aktualisieren: beide Listen sofort neu abrufen.')

def rollback():
    folder=LATEST.resolve(strict=True)
    records=json.loads((folder/'manifest.json').read_text())
    for item in records:
        if digest(Path(item['path']))!=item['after']:raise RuntimeError('Datei inzwischen geändert: '+item['path'])
    for item in records:
        path=Path(item['path'])
        if item['before'] is None:path.unlink(missing_ok=True)
        else:shutil.copy2(folder/item['backup'],path)
    reload();print('Cache-Erweiterung zurückgenommen.')

def backup_git():
    repo=HOME/'rpi-automotive-setup'
    def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True)
    if git('branch','--show-current').stdout.strip()!='main':raise RuntimeError('Nicht auf main.')
    git('fetch','origin');git('merge-base','--is-ancestor','origin/main','HEAD')
    mappings=[(SCRIPTS/name,'mira/userdata/scripts/'+name) for name in (*PAYLOAD,'mira_phone_ui.py')]
    mappings += [(HOME/'.kodi/addons/skin.estuary.custom/xml/custom_MiraPhone.xml','mira/skin.estuary.custom/xml/custom_MiraPhone.xml'),
                 (Path(__file__).resolve(),'tools/mira_phone_cache_v9.py')]
    paths=[relative for source,relative in mappings]
    status=git('status','--porcelain','--',*paths).stdout
    if status.strip():raise RuntimeError('Exportziele haben lokale Änderungen:\n'+status)
    for source,relative in mappings:
        target=repo/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    git('add','--',*paths)
    result=subprocess.run(['git','-C',str(repo),'diff','--cached','--quiet','--',*paths])
    if result.returncode==1:print(git('commit','--only','-m','MIRA: Telefonlisten zwischenspeichern und im Hintergrund aktualisieren','--',*paths).stdout)
    elif result.returncode:raise RuntimeError('Git-Diff fehlgeschlagen.')
    result=git('push','origin','main');print(result.stdout+result.stderr)
    print('GitHub-Sicherung abgeschlossen. Persönliche Cache-Daten wurden nicht exportiert.')

if __name__=='__main__':
    try:
        if len(sys.argv)==1:install()
        elif sys.argv[1:]==['--rollback']:rollback()
        elif sys.argv[1:]==['--backup-git']:backup_git()
        else:raise RuntimeError('Optionen: --rollback oder --backup-git')
    except Exception as error:raise SystemExit('Abgebrochen: '+str(error))
