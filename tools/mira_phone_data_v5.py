#!/usr/bin/env python3
"""MIRA Telefon V5: Kontakte und Anrufliste lesend per PBAP anbinden.
Installieren: python3 mira_phone_data_v5.py
Rollback: python3 mira_phone_data_v5.py --rollback
GitHub-Sicherung: python3 mira_phone_data_v5.py --backup-git
Anruffunktionen, SMS und Audio-Konfiguration werden nicht veraendert.
"""
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

EXPECTED_UI = '0096a27d54cccc422a0c8f96ffa0d751cb88bfdf826255cf262a39d817135ebb'
PAYLOAD = {'mira_phone_ui.py': "# MIRA_PHONE_UI_V5\nimport json\nfrom pathlib import Path\nimport sys\nimport unicodedata\nimport uuid\nimport xbmc\nimport xbmcgui\n\nW=xbmcgui.Window(11189)\n\ndef focus(cid):xbmc.executebuiltin('SetFocus(%d)' % cid)\ndef focused(cid):return xbmc.getCondVisibility('Control.HasFocus(%d)' % cid)\ndef right():return 9650 if W.getProperty('MiraPhoneView')=='sms' else 9600\n\ndef read_data():\n    path=W.getProperty('MiraPhoneDataFile')\n    if path:\n        try:return json.loads(Path(path).read_text(encoding='utf-8'))\n        except (OSError,ValueError):pass\n    return dict(status='loading',contacts=[],calls=[],loaded=[],errors={})\n\ndef letter(name):\n    text=''.join(c for c in unicodedata.normalize('NFKD',name) if not unicodedata.combining(c)).upper()\n    return text[0] if text and 'A'<=text[0]<='Z' else '#'\n\ndef render():\n    mode=W.getProperty('MiraPhoneView') or 'calls'\n    title={'calls':'Anrufliste','contacts':'Kontakte','sms':'Nachrichten'}[mode]\n    W.setProperty('MiraPhoneListTitle',title)\n    control=W.getControl(50);data=read_data();items=[];old_key=''\n    try:\n        old=control.getSelectedItem()\n        if old and W.getProperty('MiraPhoneRenderedView')==mode:old_key=old.getProperty('MiraPhoneKey')\n        old_position=control.getSelectedPosition()\n    except (RuntimeError,AttributeError):old_position=0\n    try:position=int(W.getProperty('MiraPhonePosition.'+mode) or '0')\n    except ValueError:position=0\n    if W.getProperty('MiraPhoneRenderedView')==mode:position=max(0,old_position)\n    records=data.get(mode,[]) if mode in ('contacts','calls') else []\n    if mode=='contacts' and records:\n        item=xbmcgui.ListItem(label='A–Z · Buchstabe wählen')\n        item.setProperty('MiraPhoneAction','az');items.append(item)\n    for record in records:\n        numbers=record.get('numbers',[])\n        if mode=='calls':\n            detail=' · '.join(x for x in (record.get('kind','Anruf'),record.get('time','')) if x)\n        else:\n            detail=numbers[0].get('display',numbers[0]['number']) if len(numbers)==1 else '%d Rufnummern' % len(numbers)\n        item=xbmcgui.ListItem(label=record['name'],label2=detail)\n        item.setProperty('MiraPhoneNumbers',json.dumps(numbers,ensure_ascii=False))\n        item.setProperty('MiraPhoneInitial',record.get('initial',letter(record['name'])))\n        item.setProperty('MiraPhoneKey',json.dumps([record['name'],numbers,record.get('time','')],ensure_ascii=False,sort_keys=True))\n        items.append(item)\n    if not items:\n        status=data.get('status','loading')\n        if mode=='sms':text='Keine Nachrichten geladen'\n        elif status=='no_device':text='Kein Telefon verbunden'\n        elif status=='multiple_devices':text='Mehrere Telefone verbunden'\n        elif mode in data.get('errors',{}) or status=='error':text=title+' nicht verfügbar'\n        elif mode not in data.get('loaded',[]):text=title+' wird geladen …'\n        else:text='Keine Kontakte mit Rufnummer' if mode=='contacts' else 'Keine Anrufe vorhanden'\n        items=[xbmcgui.ListItem(label=text)]\n    if old_key:\n        position=next((i for i,item in enumerate(items) if item.getProperty('MiraPhoneKey')==old_key),position)\n    control.reset();control.addItems(items);control.selectItem(min(position,len(items)-1))\n    W.setProperty('MiraPhoneRenderedView',mode)\n\ndef view(name):\n    old=W.getProperty('MiraPhoneView')\n    if old:\n        try:W.setProperty('MiraPhonePosition.'+old,str(max(0,W.getControl(50).getSelectedPosition())))\n        except RuntimeError:pass\n    name=name if name in ('calls','contacts','sms') else 'calls'\n    W.setProperty('MiraPhoneView',name)\n    if name!='sms':W.setProperty('MiraPhoneLastList',name)\n    render();W.setProperty('MiraPhoneLastFocus','50');focus(50)\n\ndef refresh():\n    W.setProperty('MiraPhoneRefreshToken',uuid.uuid4().hex)\n    script=Path(__file__).with_name('mira_phone_refresh.py')\n    xbmc.executebuiltin('RunScript(%s)' % script)\n\ndef select():\n    item=W.getControl(50).getSelectedItem()\n    if not item:return\n    if item.getProperty('MiraPhoneAction')=='az':\n        records=read_data().get('contacts',[])\n        letters=sorted({r.get('initial',letter(r['name'])) for r in records},key=lambda x:('ZZ' if x=='#' else x))\n        index=xbmcgui.Dialog().select('Buchstabe wählen',letters)\n        if index>=0:\n            target=next((i+1 for i,r in enumerate(records) if r.get('initial',letter(r['name']))==letters[index]),0)\n            W.getControl(50).selectItem(target)\n        return\n    try:numbers=json.loads(item.getProperty('MiraPhoneNumbers') or '[]')\n    except ValueError:return\n    if not numbers:return\n    if len(numbers)>1:\n        index=xbmcgui.Dialog().select(item.getLabel(),[n.get('label','Telefon')+' · '+n.get('display',n['number']) for n in numbers])\n        if index<0:return\n    else:index=0\n    W.setProperty('MiraPhoneNumber',numbers[index]['number']);focus(9600)\n\ndef restore():\n    try:cid=int(W.getProperty('MiraPhoneLastFocus'))\n    except ValueError:cid=50\n    focus(50 if cid==50 else right())\n\ndef main():\n    mode=sys.argv[1] if len(sys.argv)>1 else 'init'\n    if mode=='init':\n        monitor=xbmc.Monitor()\n        for attempt in range(30):\n            try:W.getControl(50);break\n            except RuntimeError:\n                if monitor.waitForAbort(0.05):return\n        W.setProperty('MiraPhoneNumber','');W.setProperty('MiraPhoneDataFile','')\n        W.setProperty('MiraPhoneRenderedView','');view('calls');refresh()\n    elif mode=='views':\n        selected=xbmcgui.Dialog().select('Telefon',['Anrufliste','Kontakte','Nachrichten','Daten aktualisieren'])\n        if 0<=selected<3:view(('calls','contacts','sms')[selected])\n        elif selected==3:refresh()\n    elif mode=='select':select()\n    elif mode=='dial':\n        if W.getProperty('MiraPhoneView')=='sms':view(W.getProperty('MiraPhoneLastList') or 'calls')\n        focus(9600)\n    elif mode=='digit':\n        digit=sys.argv[2] if len(sys.argv)>2 else ''\n        digit={'star':'*','hash':'#','plus':'+'}.get(digit,digit)\n        number=W.getProperty('MiraPhoneNumber')\n        if len(digit)==1 and digit in '0123456789*#' and len(number)<32:W.setProperty('MiraPhoneNumber',number+digit)\n        elif digit=='+' and not number:W.setProperty('MiraPhoneNumber','+')\n    elif mode=='delete':W.setProperty('MiraPhoneNumber',W.getProperty('MiraPhoneNumber')[:-1])\n    elif mode=='back':\n        if focused(50):xbmc.executebuiltin('ActivateWindow(Home)')\n        else:focus(50)\n    elif mode in ('left','right'):\n        if focused(9001) or focused(9003):focus(9003 if focused(9001) else 9001)\n        elif focused(9002) or focused(9004):focus(9004 if focused(9002) else 9002)\n        else:focus(50 if mode=='left' else right())\n    elif mode in ('up','down'):\n        header=focused(9001) or focused(9003);footer=focused(9002) or focused(9004)\n        if (mode=='down' and header) or (mode=='up' and footer):restore()\n        elif not header and not footer:\n            W.setProperty('MiraPhoneLastFocus',str(W.getFocusId()));focus(9001 if mode=='up' else 9002)\n    elif mode=='list':focus(50)\n\nif __name__=='__main__':main()\n", 'mira_phone_data.py': '#!/usr/bin/env python3\n"""Read-only PBAP worker. No call, message, read-status or audio mutations."""\nimport argparse\nimport codecs\nfrom datetime import datetime\nimport json\nimport os\nfrom pathlib import Path\nimport quopri\nimport re\nimport tempfile\nimport time\nimport unicodedata\n\n\ndef unescape(value):\n    return re.sub(r\'\\\\([nN,;\\\\])\',lambda m:\'\\n\' if m[1].lower()==\'n\' else m[1],value)\n\n\ndef normalize(value):\n    value=re.sub(r\'^tel:\', \'\', value, flags=re.I).split(\';\',1)[0]\n    return (\'+\' if value.strip().startswith(\'+\') else \'\')+\'\'.join(re.findall(r\'[0-9]\',value))\n\n\ndef initial(name):\n    value=\'\'.join(c for c in unicodedata.normalize(\'NFKD\',name) if not unicodedata.combining(c)).upper()\n    return value[0] if value and \'A\'<=value[0]<=\'Z\' else \'#\'\n\n\ndef parse_cards(text):\n    lines=[]\n    for line in text.replace(\'\\r\\n\',\'\\n\').splitlines():\n        if lines and lines[-1].endswith(\'=\') and \'ENCODING=QUOTED-PRINTABLE\' in lines[-1].upper():\n            lines[-1]=lines[-1][:-1]+line.lstrip()\n        elif line.startswith((\' \',\'\\t\')) and lines:\n            lines[-1]+=line[1:]\n        else: lines.append(line)\n    records=[];current=None\n    for line in lines:\n        if line.upper()==\'BEGIN:VCARD\': current=[]\n        elif line.upper()==\'END:VCARD\':\n            if current is not None: records.append(current)\n            current=None\n        elif current is not None and \':\' in line:\n            head,value=line.split(\':\',1);parts=head.split(\';\');field=parts[0].rsplit(\'.\',1)[-1].upper()\n            params=[p.upper() for p in parts[1:]]\n            if \'ENCODING=QUOTED-PRINTABLE\' in params:\n                charset=next((p.split(\'=\',1)[1] for p in parts[1:] if p.upper().startswith(\'CHARSET=\')),\'utf-8\')\n                try: value=quopri.decodestring(value).decode(charset,errors=\'replace\')\n                except (LookupError,ValueError): value=quopri.decodestring(value).decode(\'utf-8\',errors=\'replace\')\n            current.append((field,params,value))\n    return records\n\n\ndef phone_record(card):\n    def first(key):return next((value for field,params,value in card if field==key),\'\')\n    name=unescape(first(\'FN\')).strip()\n    if not name:\n        parts=re.split(r\'(?<!\\\\);\',first(\'N\'))\n        if len(parts)>1:name=\' \'.join(unescape(x) for x in (parts[1:3]+parts[:1]) if x).strip()\n    numbers=[];seen=set()\n    for field,params,value in card:\n        if field!=\'TEL\':continue\n        raw=unescape(value).strip();number=normalize(raw)\n        if not any(c.isdigit() for c in number) or number in seen:continue\n        seen.add(number);types=\',\'.join(params)\n        label=\'Mobil\' if \'CELL\' in types else \'Privat\' if \'HOME\' in types else \'Arbeit\' if \'WORK\' in types else \'Telefon\'\n        numbers.append(dict(number=number,display=raw,label=label))\n    return dict(name=name or (numbers[0][\'display\'] if numbers else \'Unbekannt\'),numbers=numbers)\n\n\ndef contacts_from(text):\n    result=[phone_record(card) for card in parse_cards(text)]\n    result=[record for record in result if record[\'numbers\']]\n    result.sort(key=lambda r:\'\'.join(c for c in unicodedata.normalize(\'NFKD\',r[\'name\']).casefold() if not unicodedata.combining(c)))\n    for record in result:record[\'initial\']=initial(record[\'name\'])\n    return result\n\n\ndef calls_from(text,contacts):\n    names={}\n    for contact in contacts:\n        for number in contact[\'numbers\']:names.setdefault(number[\'number\'],set()).add(contact[\'name\'])\n    result=[]\n    for card in parse_cards(text):\n        record=phone_record(card)\n        if record[\'numbers\']:\n            number=record[\'numbers\'][0][\'number\'];candidates=names.get(number,set())\n            if len(candidates)==1 and (record[\'name\']==record[\'numbers\'][0][\'display\'] or record[\'name\']==\'Unbekannt\'):\n                record[\'name\']=next(iter(candidates))\n        stamp=\'\';kind=\'Anruf\';sort=\'\'\n        for field,params,value in card:\n            if field!=\'X-IRMC-CALL-DATETIME\':continue\n            flags=\',\'.join(params)\n            kind=\'Verpasst\' if \'MISSED\' in flags else \'Ausgehend\' if \'DIALED\' in flags else \'Eingehend\' if \'RECEIVED\' in flags else \'Anruf\'\n            try:\n                dt=datetime.fromisoformat(value.strip().replace(\'Z\',\'+00:00\'))\n                if dt.tzinfo:dt=dt.astimezone()\n                stamp=dt.strftime(\'%d.%m.%Y %H:%M\');sort=dt.strftime(\'%Y%m%d%H%M%S\')\n            except ValueError:pass\n        record.update(kind=kind,time=stamp,sort=sort)\n        if not record[\'numbers\'] and record[\'name\']==\'Unbekannt\':record[\'name\']=\'Unbekannte Rufnummer\'\n        result.append(record)\n    result.sort(key=lambda r:r[\'sort\'],reverse=True)\n    return result\n\n\ndef main():\n    parser=argparse.ArgumentParser();parser.add_argument(\'--output\',required=True);args=parser.parse_args()\n    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)\n    data=dict(status=\'loading\',contacts=[],calls=[],loaded=[],errors={})\n    def publish():\n        fd,name=tempfile.mkstemp(prefix=\'.phone-\',dir=output.parent)\n        try:\n            with os.fdopen(fd,\'w\',encoding=\'utf-8\') as handle:json.dump(data,handle,ensure_ascii=False)\n            os.replace(name,output)\n        finally:Path(name).unlink(missing_ok=True)\n    publish();session=None;client=None\n    try:\n        import dbus\n        from dbus.mainloop.glib import DBusGMainLoop\n        from gi.repository import GLib\n        DBusGMainLoop(set_as_default=True)\n        system=dbus.SystemBus()\n        objects=dbus.Interface(system.get_object(\'org.bluez\',\'/\'),\'org.freedesktop.DBus.ObjectManager\').GetManagedObjects(timeout=15)\n        devices=[]\n        for path,interfaces in objects.items():\n            device=interfaces.get(\'org.bluez.Device1\',{})\n            uuids=[str(x).lower() for x in device.get(\'UUIDs\',[])]\n            if device.get(\'Connected\',False) and \'0000112f-0000-1000-8000-00805f9b34fb\' in uuids:\n                devices.append(str(device[\'Address\']))\n        if len(devices)!=1:\n            data[\'status\']=\'no_device\' if not devices else \'multiple_devices\';publish();return\n        bus=dbus.SessionBus();states={};context=GLib.MainContext.default()\n        def changed(interface,values,invalidated,path=None):\n            if str(interface)==\'org.bluez.obex.Transfer1\':states.setdefault(str(path),{}).update(dict(values))\n        bus.add_signal_receiver(changed,signal_name=\'PropertiesChanged\',dbus_interface=\'org.freedesktop.DBus.Properties\',bus_name=\'org.bluez.obex\',path_keyword=\'path\')\n        client=dbus.Interface(bus.get_object(\'org.bluez.obex\',\'/org/bluez/obex\'),\'org.bluez.obex.Client1\')\n        session=client.CreateSession(devices[0],dbus.Dictionary({\'Target\':\'pbap\'},signature=\'sv\'),timeout=60)\n        pbap=dbus.Interface(bus.get_object(\'org.bluez.obex\',session),\'org.bluez.obex.PhonebookAccess1\')\n        with tempfile.TemporaryDirectory(prefix=\'mira-pbap-\'+output.stem+\'-\',dir=output.parent) as folder:\n            folder=Path(folder)\n            for book,key in ((\'pb\',\'contacts\'),(\'cch\',\'calls\')):\n                try:\n                    pbap.Select(\'int\',book,timeout=30)\n                    target=folder/(book+\'.vcf\')\n                    path,initial_props=pbap.PullAll(str(target),dbus.Dictionary({\'Format\':\'vcard30\',\'MaxCount\':dbus.UInt16(5000)},signature=\'sv\'),timeout=30)\n                    props=dbus.Interface(bus.get_object(\'org.bluez.obex\',path),\'org.freedesktop.DBus.Properties\')\n                    values=dict(initial_props);deadline=time.monotonic()+90;next_poll=0\n                    while True:\n                        while context.pending():context.iteration(False)\n                        if time.monotonic()>=next_poll:\n                            try:values.update(props.GetAll(\'org.bluez.obex.Transfer1\',timeout=5))\n                            except dbus.DBusException as error:\n                                if error.get_dbus_name()!=\'org.freedesktop.DBus.Error.UnknownObject\':raise\n                            next_poll=time.monotonic()+0.5\n                        values.update(states.get(str(path),{}));status=str(values.get(\'Status\',\'\'))\n                        if status==\'complete\':break\n                        if status==\'error\':raise RuntimeError(\'TransferError\')\n                        if time.monotonic()>deadline:raise TimeoutError(\'TransferTimeout\')\n                        time.sleep(0.05)\n                    actual=Path(str(values.get(\'Filename\',target))).resolve()\n                    if not actual.is_relative_to(folder.resolve()):raise RuntimeError(\'UnexpectedTransferPath\')\n                    text=actual.read_text(encoding=\'utf-8-sig\',errors=\'replace\')\n                    data[key]=contacts_from(text) if key==\'contacts\' else calls_from(text,data[\'contacts\'])\n                    data[\'loaded\'].append(key)\n                except Exception as error:\n                    data[\'errors\'][key]=error.get_dbus_name() if hasattr(error,\'get_dbus_name\') else type(error).__name__\n                publish()\n        data[\'status\']=\'complete\';publish()\n    except Exception as error:\n        data[\'status\']=\'error\';data[\'errors\'][\'connection\']=error.get_dbus_name() if hasattr(error,\'get_dbus_name\') else type(error).__name__;publish()\n    finally:\n        if session is not None and client is not None:\n            try:client.RemoveSession(session,timeout=10)\n            except Exception:pass\n\nif __name__==\'__main__\':main()\n', 'mira_phone_refresh.py': "# MIRA_PHONE_REFRESH_V5\nimport fcntl\nimport json\nimport os\nfrom pathlib import Path\nimport re\nimport runpy\nimport shutil\nimport subprocess\nimport time\nimport xbmc\nimport xbmcgui\n\n\ndef main():\n    root=Path.home()/'.cache/mira-phone';root.mkdir(parents=True,exist_ok=True,mode=0o700);root.chmod(0o700)\n    lock=open(root/'refresh.lock','a')\n    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)\n    except BlockingIOError:lock.close();return\n    window=xbmcgui.Window(11189);monitor=xbmc.Monitor();worker=None;output=None;token='';signature=None;last_mode='';failed=False\n    ui=runpy.run_path(str(Path(__file__).with_name('mira_phone_ui.py')))\n    def stop():\n        nonlocal worker,output\n        if worker is not None and worker.poll() is None:\n            worker.terminate()\n            try:worker.wait(timeout=3)\n            except subprocess.TimeoutExpired:worker.kill();worker.wait(timeout=3)\n        worker=None\n        if output is not None:\n            output.unlink(missing_ok=True)\n            for folder in root.glob('mira-pbap-'+output.stem+'-*'):\n                if folder.is_dir():shutil.rmtree(folder)\n        output=None\n    try:\n        while not monitor.abortRequested() and xbmc.getCondVisibility('Window.IsActive(1189)'):\n            request=window.getProperty('MiraPhoneRefreshToken')\n            if request!=token and re.fullmatch('[a-f0-9]{32}',request or ''):\n                stop();token=request;output=root/('session-'+token+'.json');signature=None;failed=False\n                window.setProperty('MiraPhoneDataFile',str(output))\n                worker=subprocess.Popen(['/usr/bin/python3',str(Path(__file__).with_name('mira_phone_data.py')),'--output',str(output)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)\n            if output is not None:\n                if worker is not None and worker.poll() not in (None,0) and not failed:\n                    failed=True\n                    fd,name=__import__('tempfile').mkstemp(prefix='.error-',dir=root)\n                    with os.fdopen(fd,'w') as handle:json.dump(dict(status='error',contacts=[],calls=[],loaded=[],errors={}),handle)\n                    os.replace(name,output)\n                try:current=(output.stat().st_mtime_ns,output.stat().st_size)\n                except OSError:current=None\n                mode=window.getProperty('MiraPhoneView')\n                if current!=signature or mode!=last_mode:\n                    ui['render']();signature=current;last_mode=mode\n            if monitor.waitForAbort(0.15):break\n    except Exception:\n        xbmc.log('[MIRA Phone] Aktualisierung fehlgeschlagen; keine persoenlichen Daten protokolliert.',xbmc.LOGERROR)\n        if xbmc.getCondVisibility('Window.IsActive(1189)'):\n            xbmcgui.Dialog().notification('Telefon','Daten konnten nicht geladen werden.')\n    finally:\n        stop()\n        if window.getProperty('MiraPhoneRefreshToken')==token:window.clearProperty('MiraPhoneDataFile')\n        lock.close()\n\nif __name__=='__main__':main()\n"}

def targets(home):
    userdata=home/'.kodi/userdata'
    skin=home/'.kodi/addons/skin.estuary.custom'
    return [skin/'xml/custom_MiraPhone.xml']+[userdata/'scripts'/name for name in PAYLOAD]

def prepare(home):
    files=targets(home);window=files[0]
    current=window.read_bytes();root=ET.fromstring(current)
    if root.get('id')!='1189':raise RuntimeError('Unerwartetes Telefonfenster.')
    ui=home/'.kodi/userdata/scripts/mira_phone_ui.py'
    if hashlib.sha256(ui.read_bytes()).hexdigest()!=EXPECTED_UI:
        raise RuntimeError('Telefon-Skript weicht vom bekannten Stand ab. Bitte aktuelle Datei schicken; nichts geaendert.')
    for file in files[2:]:
        if file.exists():raise RuntimeError('Neue Zieldatei existiert bereits: '+str(file))
    listing=root.find(".//control[@id='50']")
    footer=root.find(".//include[@content='RNSE_GlobalFooter']")
    header=root.find(".//include[@content='RNSE_AppHeader']")
    if listing is None or footer is None or header is None:raise RuntimeError('Liste, Header oder Footer fehlt.')
    invariants=(ET.tostring(header),ET.tostring(footer))
    dial_before={node.get('id'):ET.tostring(node) for node in root.iter('control') if node.get('id') and 9600<=int(node.get('id'))<=9612}
    def put(parent,name,text):
        node=parent.find(name)
        if node is None:node=ET.SubElement(parent,name)
        node.text=str(text);return node
    put(listing,'onclick','RunScript(%s,select)' % ui)
    for name in ('itemlayout','focusedlayout'):
        layout=listing.find(name)
        if layout is None:raise RuntimeError('Listenlayout fehlt.')
        layout.set('height','110')
        for node in list(layout):
            if node.get('type')=='label':layout.remove(node)
        for y,height,font,color,text in (
            (4,58,'font45','FFF0F2F5','$INFO[ListItem.Label]'),
            (62,38,'font35','FFB3BAC5','$INFO[ListItem.Label2]')
        ):
            node=ET.SubElement(layout,'control',{'type':'label'})
            for key,value in dict(left=22,top=y,width=800,height=height,font=font,textcolor=color,
                                  aligny='center',scroll='true',label=text).items():put(node,key,value)
        image=layout.find("control[@type='image']")
        if image is not None:put(image,'height','106')
    assert (ET.tostring(header),ET.tostring(footer))==invariants
    assert dial_before=={node.get('id'):ET.tostring(node) for node in root.iter('control') if node.get('id') and 9600<=int(node.get('id'))<=9612}
    ET.indent(root,space='    ')
    data={window:ET.tostring(root,encoding='utf-8',xml_declaration=True)}
    ET.fromstring(data[window])
    for name,source in PAYLOAD.items():
        target=home/'.kodi/userdata/scripts'/name
        compile(source,str(target),'exec');data[target]=source.encode('utf-8')
    return data

def atomic(path,data,mode=0o644):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.phone-data-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as handle:handle.write(data)
        os.chmod(name,mode);os.replace(name,path)
    finally:Path(name).unlink(missing_ok=True)

def reload_kodi():
    command=shutil.which('kodi-send')
    if command:
        result=subprocess.run([command,'--action=ReloadSkin()'],capture_output=True,text=True,timeout=10)
        print('Skin-Reload angefordert.' if not result.returncode else 'Reload fehlgeschlagen: '+result.stderr.strip())
    else:print('kodi-send fehlt. Bitte Ausgabe schicken.')

def install(home):
    files=prepare(home)
    userdata=home/'.kodi/userdata';directory=userdata/'mira-backups'
    latest=directory/'phone-data-v5-latest'
    if latest.exists() and not latest.is_symlink():raise RuntimeError('Backup-Verknuepfung ist belegt.')
    backup=directory/('phone-data-v5-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir(parents=True)
    records=[]
    for index,(path,data) in enumerate(files.items()):
        existed=path.exists();mode=path.stat().st_mode & 0o777 if existed else 0o644
        if existed:shutil.copy2(path,backup/str(index))
        records.append(dict(path=str(path),original=str(index),existed=existed,mode=mode,sha=hashlib.sha256(data).hexdigest()))
    (backup/'manifest.json').write_text(json.dumps(records,indent=2))
    written=[]
    try:
        for record,(path,data) in zip(records,files.items()):written.append(record);atomic(path,data,record['mode'])
        ET.parse(next(iter(files)))
        for path in list(files)[1:]:compile(path.read_bytes(),str(path),'exec')
        link=directory/('link-'+backup.name);link.symlink_to(backup,target_is_directory=True);os.replace(link,latest)
    except Exception:
        for record in reversed(written):
            path=Path(record['path'])
            if record['existed']:atomic(path,(backup/record['original']).read_bytes(),record['mode'])
            else:path.unlink(missing_ok=True)
        raise
    print('Kontakte und Anrufliste angebunden. Backup:',backup)
    print('Es werden keine Anrufe gestartet und keine SMS veraendert.')
    reload_kodi()

def rollback(home):
    backup=home/'.kodi/userdata/mira-backups/phone-data-v5-latest'
    if not backup.is_symlink():raise RuntimeError('Kein V5-Backup vorhanden.')
    backup=backup.resolve(strict=True);records=json.loads((backup/'manifest.json').read_text())
    for record in records:
        path=Path(record['path'])
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha']:
            raise RuntimeError('Datei inzwischen veraendert. Rollback gestoppt: '+str(path))
        if record['existed'] and not (backup/record['original']).is_file():raise RuntimeError('Original fehlt.')
    for record in reversed(records):
        path=Path(record['path'])
        if record['existed']:atomic(path,(backup/record['original']).read_bytes(),record['mode'])
        else:path.unlink()
    print('Vorheriger Stand wiederhergestellt.')
    reload_kodi()

def backup_git(home):
    repo=home/'rpi-automotive-setup'
    def git(*args,check=True):
        result=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True)
        if check and result.returncode:raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return result
    if git('branch','--show-current').stdout.strip()!='main':raise RuntimeError('Nicht auf main.')
    remote=git('remote','get-url','origin').stdout.replace(':','/')
    if 'github.com/grep-purpose/rpi-automotive-setup' not in remote:raise RuntimeError('Unerwartetes Repository.')
    git('fetch','origin')
    if git('merge-base','--is-ancestor','origin/main','HEAD',check=False).returncode:
        raise RuntimeError('GitHub hat neue Commits. Bitte Ausgabe schicken; nichts exportiert.')
    sources={}
    skin=home/'.kodi/addons/skin.estuary.custom'
    for relative in ('xml/Home.xml','xml/custom_MiraPhone.xml','media/home/mmi_icons_v1/phone.png','media/mira/phone-delete-arrow-v3.png','media/mira/phone-key-v4.png','media/mira/phone-call-v4.png'):
        sources[skin/relative]='mira/skin.estuary.custom/'+relative
    for name in PAYLOAD:sources[home/'.kodi/userdata/scripts'/name]='mira/userdata/scripts/'+name
    sources[home/'.kodi/userdata/keymaps/zz_mira_phone.xml']='mira/userdata/keymaps/zz_mira_phone.xml'
    sources[Path(__file__).resolve()]='tools/mira_phone_data_v5.py'
    paths=list(sources.values())
    if not all(p.is_file() for p in sources):raise RuntimeError('Eine Quelldatei fehlt.')
    status=git('status','--porcelain','--',*paths).stdout
    if status.strip():raise RuntimeError('Exportziele enthalten lokale Aenderungen:\n'+status)
    for source,relative in sources.items():
        target=repo/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    git('add','--',*paths)
    result=git('diff','--cached','--quiet','--',*paths,check=False)
    if result.returncode==1:print(git('commit','--only','-m','MIRA: Kontakte und Anrufliste ueber PBAP','--',*paths).stdout)
    elif result.returncode:raise RuntimeError('Git-Pruefung fehlgeschlagen.')
    result=git('push','origin','main',check=False);print(result.stderr)
    if result.returncode:raise RuntimeError('Push fehlgeschlagen; Commit bleibt lokal erhalten. Bitte Ausgabe schicken.')
    print('GitHub-Sicherung abgeschlossen.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group();group.add_argument('--rollback',action='store_true');group.add_argument('--backup-git',action='store_true')
    args=parser.parse_args()
    try:
        if args.rollback:rollback(Path.home())
        elif args.backup_git:backup_git(Path.home())
        else:install(Path.home())
    except Exception as error:raise SystemExit('STOPP: '+str(error))

if __name__=='__main__':main()
