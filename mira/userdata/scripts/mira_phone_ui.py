# MIRA_PHONE_UI_V5
# MIRA_PHONE_SELECT_V6
import json
from pathlib import Path
import sys
import unicodedata
import uuid
import xbmc
import xbmcgui

W=xbmcgui.Window(11189)

def focus(cid):xbmc.executebuiltin('SetFocus(%d)' % cid)
def focused(cid):return xbmc.getCondVisibility('Control.HasFocus(%d)' % cid)
def right():return 9650 if W.getProperty('MiraPhoneView')=='sms' else 9600

def read_data():
    path=W.getProperty('MiraPhoneDataFile')
    if path:
        try:return json.loads(Path(path).read_text(encoding='utf-8'))
        except (OSError,ValueError):pass
    return dict(status='loading',contacts=[],calls=[],loaded=[],errors={})

def letter(name):
    text=''.join(c for c in unicodedata.normalize('NFKD',name) if not unicodedata.combining(c)).upper()
    return text[0] if text and 'A'<=text[0]<='Z' else '#'

def render():
    mode=W.getProperty('MiraPhoneView') or 'calls'
    title={'calls':'Anrufliste','contacts':'Kontakte','sms':'Nachrichten'}[mode]
    W.setProperty('MiraPhoneListTitle',title)
    control=W.getControl(50);data=read_data();items=[];old_key=''
    try:
        old=control.getSelectedItem()
        if old and W.getProperty('MiraPhoneRenderedView')==mode:old_key=old.getProperty('MiraPhoneKey')
        old_position=control.getSelectedPosition()
    except (RuntimeError,AttributeError):old_position=0
    try:position=int(W.getProperty('MiraPhonePosition.'+mode) or '0')
    except ValueError:position=0
    if W.getProperty('MiraPhoneRenderedView')==mode:position=max(0,old_position)
    records=data.get(mode,[]) if mode in ('contacts','calls') else []
    if mode=='contacts' and records:
        item=xbmcgui.ListItem(label='A–Z · Buchstabe wählen')
        item.setProperty('MiraPhoneAction','az');items.append(item)
    for record in records:
        numbers=record.get('numbers',[])
        if mode=='calls':
            detail=' · '.join(x for x in (record.get('kind','Anruf'),record.get('time','')) if x)
        else:
            detail=numbers[0].get('display',numbers[0]['number']) if len(numbers)==1 else '%d Rufnummern' % len(numbers)
        item=xbmcgui.ListItem(label=record['name'],label2=detail)
        item.setProperty('MiraPhoneNumbers',json.dumps(numbers,ensure_ascii=False))
        item.setProperty('MiraPhoneInitial',record.get('initial',letter(record['name'])))
        item.setProperty('MiraPhoneKey',json.dumps([record['name'],numbers,record.get('time','')],ensure_ascii=False,sort_keys=True))
        items.append(item)
    if not items:
        status=data.get('status','loading')
        if mode=='sms':text='Keine Nachrichten geladen'
        elif status=='no_device':text='Kein Telefon verbunden'
        elif status=='multiple_devices':text='Mehrere Telefone verbunden'
        elif mode in data.get('errors',{}) or status=='error':text=title+' nicht verfügbar'
        elif mode not in data.get('loaded',[]):text=title+' wird geladen …'
        else:text='Keine Kontakte mit Rufnummer' if mode=='contacts' else 'Keine Anrufe vorhanden'
        items=[xbmcgui.ListItem(label=text)]
    if old_key:
        position=next((i for i,item in enumerate(items) if item.getProperty('MiraPhoneKey')==old_key),position)
    control.reset();control.addItems(items);control.selectItem(min(position,len(items)-1))
    W.setProperty('MiraPhoneRenderedView',mode)

def view(name):
    old=W.getProperty('MiraPhoneView')
    if old:
        try:W.setProperty('MiraPhonePosition.'+old,str(max(0,W.getControl(50).getSelectedPosition())))
        except RuntimeError:pass
    name=name if name in ('calls','contacts','sms') else 'calls'
    W.setProperty('MiraPhoneView',name)
    if name!='sms':W.setProperty('MiraPhoneLastList',name)
    render();W.setProperty('MiraPhoneLastFocus','50');focus(50)

def refresh():
    W.setProperty('MiraPhoneRefreshToken',uuid.uuid4().hex)
    script=Path(__file__).with_name('mira_phone_refresh.py')
    xbmc.executebuiltin('RunScript(%s)' % script)

def select():
    mode=W.getProperty('MiraPhoneView')
    def native(name):
        return xbmc.getInfoLabel('Container(50).ListItem.'+name)
    action=native('Property(MiraPhoneAction)')
    name=native('Label')
    raw=native('Property(MiraPhoneNumbers)')
    current=xbmc.getInfoLabel('Container(50).CurrentItem').strip()
    records=read_data().get(mode,[]) if mode in ('contacts','calls') else []
    if action=='az' or (mode=='contacts' and records and current=='1'):
        letters=sorted(
            {r.get('initial',letter(r['name'])) for r in records},
            key=lambda x:('ZZ' if x=='#' else x)
        )
        chosen=xbmcgui.Dialog().select('Buchstabe wählen',letters)
        if chosen>=0:
            target=next(
                (i+1 for i,r in enumerate(records)
                 if r.get('initial',letter(r['name']))==letters[chosen]),
                0
            )
            xbmc.executebuiltin('SetFocus(50,%d,absolute)' % target)
        return
    try:
        numbers=json.loads(raw or '[]')
    except ValueError:
        numbers=[]
    if not numbers:
        try:
            index=int(current)-1-(1 if mode=='contacts' and records else 0)
        except ValueError:
            index=-1
        if 0<=index<len(records) and name==records[index]['name']:
            numbers=records[index].get('numbers',[])
    numbers=[
        n for n in numbers
        if isinstance(n,dict)
        and isinstance(n.get('number'),str)
        and n['number']
    ]
    xbmc.log(
        '[MIRA Phone Select V6] Rufnummern gefunden: %d' % len(numbers),
        xbmc.LOGINFO
    )
    if not numbers:
        return
    if len(numbers)>1:
        chosen=xbmcgui.Dialog().select(
            name or 'Rufnummer wählen',
            [n.get('label','Telefon')+' · '+n.get('display',n['number'])
             for n in numbers]
        )
        if chosen<0:
            return
    else:
        chosen=0
    W.setProperty('MiraPhoneNumber',numbers[chosen]['number'])
    focus(9600)


def restore():
    try:cid=int(W.getProperty('MiraPhoneLastFocus'))
    except ValueError:cid=50
    focus(50 if cid==50 else right())

def main():
    mode=sys.argv[1] if len(sys.argv)>1 else 'init'
    if mode=='init':
        monitor=xbmc.Monitor()
        for attempt in range(30):
            try:W.getControl(50);break
            except RuntimeError:
                if monitor.waitForAbort(0.05):return
        W.setProperty('MiraPhoneNumber','');W.setProperty('MiraPhoneDataFile','')
        W.setProperty('MiraPhoneRenderedView','');view('calls');refresh()
    elif mode=='views':
        selected=xbmcgui.Dialog().select('Telefon',['Anrufliste','Kontakte','Nachrichten','Daten aktualisieren'])
        if 0<=selected<3:view(('calls','contacts','sms')[selected])
        elif selected==3:refresh()
    elif mode=='select':select()
    elif mode=='dial':
        if W.getProperty('MiraPhoneView')=='sms':view(W.getProperty('MiraPhoneLastList') or 'calls')
        focus(9600)
    elif mode=='digit':
        digit=sys.argv[2] if len(sys.argv)>2 else ''
        digit={'star':'*','hash':'#','plus':'+'}.get(digit,digit)
        number=W.getProperty('MiraPhoneNumber')
        if len(digit)==1 and digit in '0123456789*#' and len(number)<32:W.setProperty('MiraPhoneNumber',number+digit)
        elif digit=='+' and not number:W.setProperty('MiraPhoneNumber','+')
    elif mode=='delete':W.setProperty('MiraPhoneNumber',W.getProperty('MiraPhoneNumber')[:-1])
    elif mode=='back':
        if focused(50):xbmc.executebuiltin('ActivateWindow(Home)')
        else:focus(50)
    elif mode in ('left','right'):
        if focused(9001) or focused(9003):focus(9003 if focused(9001) else 9001)
        elif focused(9002) or focused(9004):focus(9004 if focused(9002) else 9002)
        else:focus(50 if mode=='left' else right())
    elif mode in ('up','down'):
        header=focused(9001) or focused(9003);footer=focused(9002) or focused(9004)
        if (mode=='down' and header) or (mode=='up' and footer):restore()
        elif not header and not footer:
            W.setProperty('MiraPhoneLastFocus',str(W.getFocusId()));focus(9001 if mode=='up' else 9002)
    elif mode=='list':focus(50)

if __name__=='__main__':main()
