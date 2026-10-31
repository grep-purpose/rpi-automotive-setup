# MIRA_PHONE_FOOTER_V18
import xbmc
import xbmcgui

HOME = xbmcgui.Window(10000)
PHONE = xbmcgui.Window(11189)

def destination(connected, present):
    return 1189 if connected == 'true' or present == 'true' else 1160

def main():
    if xbmcgui.getCurrentWindowId() == 11189:
        xbmc.executebuiltin('ActivateWindow(1160)')
        return
    target = destination(HOME.getProperty('RNSE.Phone.Connected'),
                         PHONE.getProperty('MiraPhoneCallPresent'))
    if target == 1160:
        xbmc.executebuiltin('ActivateWindow(1160)')
        return
    # Entering via the footer does not arm the popup's automatic return rule.
    was_phone = xbmcgui.getCurrentWindowId() == 11189
    token = PHONE.getProperty('MiraPhoneRefreshToken')
    if not was_phone:
        xbmc.executebuiltin('ActivateWindow(1189)')
    if PHONE.getProperty('MiraPhoneCallPresent') != 'true':
        return  # The existing onload action owns normal list focus.
    monitor = xbmc.Monitor()
    entered = was_phone
    for _ in range(50):
        current = xbmcgui.getCurrentWindowId()
        if entered and current != 11189:
            return
        entered = entered or current == 11189
        ready = was_phone or PHONE.getProperty('MiraPhoneRefreshToken') != token
        if ready and current == 11189 and xbmcgui.getCurrentWindowDialogId() == 9999:
            if PHONE.getProperty('MiraPhoneCallPresent') != 'true':
                return
            control = 9652 if PHONE.getProperty('MiraPhoneCallCanAnswer') == 'true' else 9651
            if xbmc.getCondVisibility('Control.IsVisible(%d)' % control):
                xbmc.executebuiltin('SetFocus(%d)' % control)
                return
        if monitor.waitForAbort(0.1):
            return

if __name__ == '__main__':
    main()
