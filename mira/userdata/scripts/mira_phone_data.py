#!/usr/bin/env python3
"""Read-only PBAP worker. No call, message, read-status or audio mutations."""
import argparse
import codecs
from datetime import datetime
import json
import os
from pathlib import Path
import quopri
import re
import tempfile
import time
import unicodedata


def unescape(value):
    return re.sub(r'\\([nN,;\\])',lambda m:'\n' if m[1].lower()=='n' else m[1],value)


def normalize(value):
    value=re.sub(r'^tel:', '', value, flags=re.I).split(';',1)[0]
    return ('+' if value.strip().startswith('+') else '')+''.join(re.findall(r'[0-9]',value))


def initial(name):
    value=''.join(c for c in unicodedata.normalize('NFKD',name) if not unicodedata.combining(c)).upper()
    return value[0] if value and 'A'<=value[0]<='Z' else '#'


def parse_cards(text):
    lines=[]
    for line in text.replace('\r\n','\n').splitlines():
        if lines and lines[-1].endswith('=') and 'ENCODING=QUOTED-PRINTABLE' in lines[-1].upper():
            lines[-1]=lines[-1][:-1]+line.lstrip()
        elif line.startswith((' ','\t')) and lines:
            lines[-1]+=line[1:]
        else: lines.append(line)
    records=[];current=None
    for line in lines:
        if line.upper()=='BEGIN:VCARD': current=[]
        elif line.upper()=='END:VCARD':
            if current is not None: records.append(current)
            current=None
        elif current is not None and ':' in line:
            head,value=line.split(':',1);parts=head.split(';');field=parts[0].rsplit('.',1)[-1].upper()
            params=[p.upper() for p in parts[1:]]
            if 'ENCODING=QUOTED-PRINTABLE' in params:
                charset=next((p.split('=',1)[1] for p in parts[1:] if p.upper().startswith('CHARSET=')),'utf-8')
                try: value=quopri.decodestring(value).decode(charset,errors='replace')
                except (LookupError,ValueError): value=quopri.decodestring(value).decode('utf-8',errors='replace')
            current.append((field,params,value))
    return records


def phone_record(card):
    def first(key):return next((value for field,params,value in card if field==key),'')
    name=unescape(first('FN')).strip()
    if not name:
        parts=re.split(r'(?<!\\);',first('N'))
        if len(parts)>1:name=' '.join(unescape(x) for x in (parts[1:3]+parts[:1]) if x).strip()
    numbers=[];seen=set()
    for field,params,value in card:
        if field!='TEL':continue
        raw=unescape(value).strip();number=normalize(raw)
        if not any(c.isdigit() for c in number) or number in seen:continue
        seen.add(number);types=','.join(params)
        label='Mobil' if 'CELL' in types else 'Privat' if 'HOME' in types else 'Arbeit' if 'WORK' in types else 'Telefon'
        numbers.append(dict(number=number,display=raw,label=label))
    return dict(name=name or (numbers[0]['display'] if numbers else 'Unbekannt'),numbers=numbers)


def contacts_from(text):
    result=[phone_record(card) for card in parse_cards(text)]
    result=[record for record in result if record['numbers']]
    result.sort(key=lambda r:''.join(c for c in unicodedata.normalize('NFKD',r['name']).casefold() if not unicodedata.combining(c)))
    for record in result:record['initial']=initial(record['name'])
    return result


def calls_from(text,contacts):
    names={}
    for contact in contacts:
        for number in contact['numbers']:names.setdefault(number['number'],set()).add(contact['name'])
    result=[]
    for card in parse_cards(text):
        record=phone_record(card)
        if record['numbers']:
            number=record['numbers'][0]['number'];candidates=names.get(number,set())
            if len(candidates)==1 and (record['name']==record['numbers'][0]['display'] or record['name']=='Unbekannt'):
                record['name']=next(iter(candidates))
        stamp='';kind='Anruf';sort=''
        for field,params,value in card:
            if field!='X-IRMC-CALL-DATETIME':continue
            flags=','.join(params)
            kind='Verpasst' if 'MISSED' in flags else 'Ausgehend' if 'DIALED' in flags else 'Eingehend' if 'RECEIVED' in flags else 'Anruf'
            try:
                dt=datetime.fromisoformat(value.strip().replace('Z','+00:00'))
                if dt.tzinfo:dt=dt.astimezone()
                stamp=dt.strftime('%d.%m.%Y %H:%M');sort=dt.strftime('%Y%m%d%H%M%S')
            except ValueError:pass
        record.update(kind=kind,time=stamp,sort=sort)
        if not record['numbers'] and record['name']=='Unbekannt':record['name']='Unbekannte Rufnummer'
        result.append(record)
    result.sort(key=lambda r:r['sort'],reverse=True)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    data=dict(status='loading',contacts=[],calls=[],loaded=[],errors={})
    def publish():
        fd,name=tempfile.mkstemp(prefix='.phone-',dir=output.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as handle:json.dump(data,handle,ensure_ascii=False)
            os.replace(name,output)
        finally:Path(name).unlink(missing_ok=True)
    publish();session=None;client=None
    try:
        import dbus
        from dbus.mainloop.glib import DBusGMainLoop
        from gi.repository import GLib
        DBusGMainLoop(set_as_default=True)
        system=dbus.SystemBus()
        objects=dbus.Interface(system.get_object('org.bluez','/'),'org.freedesktop.DBus.ObjectManager').GetManagedObjects(timeout=15)
        devices=[]
        for path,interfaces in objects.items():
            device=interfaces.get('org.bluez.Device1',{})
            uuids=[str(x).lower() for x in device.get('UUIDs',[])]
            if device.get('Connected',False) and '0000112f-0000-1000-8000-00805f9b34fb' in uuids:
                devices.append(str(device['Address']))
        if len(devices)!=1:
            data['status']='no_device' if not devices else 'multiple_devices';publish();return
        bus=dbus.SessionBus();states={};context=GLib.MainContext.default()
        def changed(interface,values,invalidated,path=None):
            if str(interface)=='org.bluez.obex.Transfer1':states.setdefault(str(path),{}).update(dict(values))
        bus.add_signal_receiver(changed,signal_name='PropertiesChanged',dbus_interface='org.freedesktop.DBus.Properties',bus_name='org.bluez.obex',path_keyword='path')
        client=dbus.Interface(bus.get_object('org.bluez.obex','/org/bluez/obex'),'org.bluez.obex.Client1')
        session=client.CreateSession(devices[0],dbus.Dictionary({'Target':'pbap'},signature='sv'),timeout=60)
        pbap=dbus.Interface(bus.get_object('org.bluez.obex',session),'org.bluez.obex.PhonebookAccess1')
        with tempfile.TemporaryDirectory(prefix='mira-pbap-'+output.stem+'-',dir=output.parent) as folder:
            folder=Path(folder)
            for book,key in (('pb','contacts'),('cch','calls')):
                try:
                    pbap.Select('int',book,timeout=30)
                    target=folder/(book+'.vcf')
                    path,initial_props=pbap.PullAll(str(target),dbus.Dictionary({'Format':'vcard30','MaxCount':dbus.UInt16(5000)},signature='sv'),timeout=30)
                    props=dbus.Interface(bus.get_object('org.bluez.obex',path),'org.freedesktop.DBus.Properties')
                    values=dict(initial_props);deadline=time.monotonic()+90;next_poll=0
                    while True:
                        while context.pending():context.iteration(False)
                        if time.monotonic()>=next_poll:
                            try:values.update(props.GetAll('org.bluez.obex.Transfer1',timeout=5))
                            except dbus.DBusException as error:
                                if error.get_dbus_name()!='org.freedesktop.DBus.Error.UnknownObject':raise
                            next_poll=time.monotonic()+0.5
                        values.update(states.get(str(path),{}));status=str(values.get('Status',''))
                        if status=='complete':break
                        if status=='error':raise RuntimeError('TransferError')
                        if time.monotonic()>deadline:raise TimeoutError('TransferTimeout')
                        time.sleep(0.05)
                    actual=Path(str(values.get('Filename',target))).resolve()
                    if not actual.is_relative_to(folder.resolve()):raise RuntimeError('UnexpectedTransferPath')
                    text=actual.read_text(encoding='utf-8-sig',errors='replace')
                    data[key]=contacts_from(text) if key=='contacts' else calls_from(text,data['contacts'])
                    data['loaded'].append(key)
                except Exception as error:
                    data['errors'][key]=error.get_dbus_name() if hasattr(error,'get_dbus_name') else type(error).__name__
                publish()
        data['status']='complete';publish()
    except Exception as error:
        data['status']='error';data['errors']['connection']=error.get_dbus_name() if hasattr(error,'get_dbus_name') else type(error).__name__;publish()
    finally:
        if session is not None and client is not None:
            try:client.RemoveSession(session,timeout=10)
            except Exception:pass

if __name__=='__main__':main()
