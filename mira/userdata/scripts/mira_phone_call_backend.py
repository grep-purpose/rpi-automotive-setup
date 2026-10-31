# MIRA_PHONE_CALL_V10
# MIRA_PHONE_CALL_V7
import json
import re
import sys
import dbus


def execute(request, bus):

    # MIRA_PHONE_SIM_V8
    from pathlib import Path
    import time
    import os
    simfile = Path.home()/'.cache/mira-phone/incoming-simulation.json'
    simpath = '/mira/simulation/incoming'
    action = request.get('action', 'status')

    if action == 'simulation-stop':
        simfile.unlink(missing_ok=True)
        return {'ok': True, 'message': 'Simulation beendet.'}

    if action == 'hangup' and request.get('path') == simpath:
        simfile.unlink(missing_ok=True)
        return {'ok': True}
    manager=dbus.Interface(bus.get_object('org.ofono','/'),'org.ofono.Manager')
    modems=[(str(p),v) for p,v in manager.GetModems(timeout=5)
            if str(v.get('Type',''))=='hfp' and bool(v.get('Powered',False))
            and bool(v.get('Online',False))
            and 'org.ofono.VoiceCallManager' in v.get('Interfaces',[])]
    if len(modems)!=1:
        raise ValueError('Kein eindeutiges, verbundenes Telefon verfügbar.')
    path,properties=modems[0]
    calls=dbus.Interface(bus.get_object('org.ofono',path),'org.ofono.VoiceCallManager')
    entries=[(str(p),v) for p,v in calls.GetCalls(timeout=5)
             if str(v.get('State',''))!='disconnected']

    if action == 'simulation-start':
        if entries:
            raise ValueError(
                'Ein echter Anruf ist vorhanden. Keine Simulation gestartet.'
            )
        simfile.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(
            simfile, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
        )
        with os.fdopen(fd, 'w') as output:
            json.dump({'expires': time.time() + 120}, output)
        return {
            'ok': True,
            'message': 'Testanruf für 120 Sekunden gestartet.'
        }

    try:
        simulated = (
            json.loads(simfile.read_text()).get('expires', 0) > time.time()
        )
    except (OSError, ValueError, TypeError, AttributeError):
        simulated = False

    if simulated and entries:
        simfile.unlink(missing_ok=True)
        simulated = False

    if simulated:
        values=json.loads(simfile.read_text())
        state=values.get('state','incoming')
        if action=='status':
            return {'ok':True,'calls':[{'path':simpath,'state':state,
                'number':'','name':'MIRA Testanruf · Simulation',
                'start':values.get('start','')}]}
        if action=='answer':
            if request.get('path')!=simpath or state!='incoming':
                raise ValueError('Der simulierte Anruf klingelt nicht mehr.')
            from datetime import datetime
            values['state']='active'
            values['start']=datetime.now().astimezone().isoformat()
            temporary=simfile.with_suffix('.tmp')
            fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(fd,'w') as output:json.dump(values,output)
            os.replace(temporary,simfile)
            return {'ok':True}
        raise ValueError('Simulation aktiv. Bitte zuerst den Testanruf beenden.')
    if action=='answer':
        target=request.get('path','')
        matching=[v for p,v in entries if p==target]
        if not matching or str(matching[0].get('State',''))!='incoming':
            raise ValueError('Dieser Anruf klingelt nicht mehr. Nichts angenommen.')
        dbus.Interface(bus.get_object('org.ofono',target),
                       'org.ofono.VoiceCall').Answer(timeout=10)
        return {'ok':True}
    if action=='dial':
        number=request.get('number','')
        if not isinstance(number,str) or not re.fullmatch(r'\+?[0-9]{1,32}',number):
            raise ValueError('Bitte eine gültige Telefonnummer eingeben.')
        if entries:
            raise ValueError('Es besteht bereits ein Anruf. Kein weiterer Anruf gestartet.')
        calls.Dial(number,'default',timeout=20)
        return {'ok':True}
    if action=='hangup':
        target=request.get('path','')
        if target not in [p for p,v in entries]:
            raise ValueError('Dieser Anruf ist nicht mehr vorhanden.')
        dbus.Interface(bus.get_object('org.ofono',target),'org.ofono.VoiceCall').Hangup(timeout=10)
        return {'ok':True}
    if action!='status':
        raise ValueError('Unbekannte Telefonaktion.')
    return {'ok':True,'calls':[{'path':p,'state':str(v.get('State','')),
        'number':str(v.get('LineIdentification','')),
        'name':str(v.get('Name','')),'start':str(v.get('StartTime',''))} for p,v in entries]}

if __name__=='__main__':
    try:
        result=execute(json.load(sys.stdin),dbus.SystemBus())
    except ValueError as error:
        result={'ok':False,'error':str(error)}
    except dbus.DBusException as error:
        result={'ok':False,'error':'oFono: '+error.get_dbus_name()}
    except Exception:
        result={'ok':False,'error':'Telefonverbindung konnte nicht abgefragt werden.'}
    print(json.dumps(result))
