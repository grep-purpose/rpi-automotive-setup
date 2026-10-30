# MIRA_PHONE_UI_V1
import sys
import xbmc
import xbmcgui
W = xbmcgui.Window(11189)
MODE = sys.argv[1] if len(sys.argv) > 1 else 'init'
def focus(cid):
    xbmc.executebuiltin('SetFocus(%d)' % cid)
def focused(cid):
    return xbmc.getCondVisibility('Control.HasFocus(%d)' % cid)
def right():
    return 9650 if W.getProperty('MiraPhoneView') == 'sms' else 9600
def view(name):
    if name not in ('calls', 'contacts', 'sms'):
        name = 'calls'
    W.setProperty('MiraPhoneView', name)
    if name != 'sms':
        W.setProperty('MiraPhoneLastList', name)
    title, empty = {
        'calls': ('Anrufliste', 'Keine Anrufe geladen'),
        'contacts': ('Kontakte', 'Keine Kontakte geladen'),
        'sms': ('Nachrichten', 'Keine Nachrichten geladen'),
    }[name]
    W.setProperty('MiraPhoneListTitle', title)
    control = W.getControl(50)
    control.reset()
    control.addItem(xbmcgui.ListItem(label=empty))
    W.setProperty('MiraPhoneLastFocus', '50')
    focus(50)
def restore():
    try:
        cid = int(W.getProperty('MiraPhoneLastFocus'))
    except ValueError:
        cid = 50
    if cid != 50:
        cid = right()
    focus(cid)
if MODE == 'init':
    monitor = xbmc.Monitor()
    for attempt in range(30):
        try:
            W.getControl(50)
            break
        except RuntimeError:
            if monitor.waitForAbort(0.05):
                sys.exit(0)
    W.setProperty('MiraPhoneNumber', '')
    view('calls')
elif MODE == 'views':
    choices = ('calls', 'contacts', 'sms')
    selected = xbmcgui.Dialog().select('Telefon', ['Anrufliste', 'Kontakte', 'Nachrichten'])
    if selected >= 0:
        view(choices[selected])
elif MODE == 'dial':
    if W.getProperty('MiraPhoneView') == 'sms':
        view(W.getProperty('MiraPhoneLastList') or 'calls')
    focus(9600)
elif MODE == 'digit':
    digit = sys.argv[2] if len(sys.argv) > 2 else ''
    digit = {'star': '*', 'hash': '#', 'plus': '+'}.get(digit, digit)
    number = W.getProperty('MiraPhoneNumber')
    if digit in '0123456789*#' and len(digit) == 1 and len(number) < 32:
        W.setProperty('MiraPhoneNumber', number + digit)
    elif digit == '+' and not number:
        W.setProperty('MiraPhoneNumber', '+')
elif MODE == 'delete':
    W.setProperty('MiraPhoneNumber', W.getProperty('MiraPhoneNumber')[:-1])
elif MODE == 'back':
    if focused(50):
        xbmc.executebuiltin('ActivateWindow(Home)')
    else:
        focus(50)
elif MODE in ('left', 'right'):
    if focused(9001) or focused(9003):
        focus(9003 if focused(9001) else 9001)
    elif focused(9002) or focused(9004):
        focus(9004 if focused(9002) else 9002)
    else:
        focus(50 if MODE == 'left' else right())
elif MODE in ('up', 'down'):
    header = focused(9001) or focused(9003)
    footer = focused(9002) or focused(9004)
    if (MODE == 'down' and header) or (MODE == 'up' and footer):
        restore()
    elif not header and not footer:
        W.setProperty('MiraPhoneLastFocus', str(W.getFocusId()))
        focus(9001 if MODE == 'up' else 9002)
elif MODE == 'list':
    focus(50)
