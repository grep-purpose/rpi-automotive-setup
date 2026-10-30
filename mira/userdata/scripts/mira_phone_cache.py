# MIRA_PHONE_CACHE_V9
from pathlib import Path
import hashlib
import json
import os
import tempfile
import time

ROOT=Path.home()/'.cache/mira-phone'

def device():
    import dbus
    bus=dbus.SystemBus()
    objects=dbus.Interface(bus.get_object('org.bluez','/'),
        'org.freedesktop.DBus.ObjectManager').GetManagedObjects(timeout=3)
    found=[]
    for interfaces in objects.values():
        props=interfaces.get('org.bluez.Device1',{})
        if props.get('Connected',False) and '0000112f-0000-1000-8000-00805f9b34fb' in [str(x).lower() for x in props.get('UUIDs',[])]:
            found.append(str(props['Address']).upper())
    return found

def path(address):
    return ROOT/('cache-v9-'+hashlib.sha256(address.upper().encode()).hexdigest()+'.json')

def load(address):
    try:
        data=json.loads(path(address).read_text())
        if data.get('device')!=address.upper():return None
        if not isinstance(data.get('contacts'),list) or not isinstance(data.get('calls'),list):return None
        if not isinstance(data.get('_cached_at'),dict):return None
        return data
    except (OSError,ValueError,AttributeError):return None

def save(data):
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700);ROOT.chmod(0o700)
    content=dict(data,status='complete',errors={})
    fd,name=tempfile.mkstemp(prefix='.cache-',dir=ROOT)
    try:
        with os.fdopen(fd,'w') as output:json.dump(content,output,ensure_ascii=False)
        os.replace(name,path(data['device']))
    finally:Path(name).unlink(missing_ok=True)

def probe():
    found=device()
    if len(found)==1 and load(found[0]) is not None:
        return str(path(found[0]))
    return ''

if __name__=='__main__':
    try:print(probe())
    except Exception:print('')
