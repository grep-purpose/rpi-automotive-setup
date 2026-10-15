import sys
import xbmc

if len(sys.argv) > 1:
    cmd = sys.argv[1]
    xbmc.log(f"[AUDI-DISPATCHER] Executing: {cmd}", level=xbmc.LOGINFO)
    xbmc.executebuiltin(cmd)
