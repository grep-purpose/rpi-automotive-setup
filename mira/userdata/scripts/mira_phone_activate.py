# MIRA_PHONE_ACTIVATE_V6
from pathlib import Path
import xbmc
import xbmcgui

if (xbmcgui.getCurrentWindowDialogId()==9999
        and xbmc.getCondVisibility('Control.HasFocus(50)')):
    script=Path(__file__).with_name('mira_phone_ui.py')
    xbmc.executebuiltin('RunScript(%s,select)' % script)
else:
    xbmc.executebuiltin('Action(Select)')
