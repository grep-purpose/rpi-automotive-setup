#!/usr/bin/env python3

import os
import signal
import subprocess

STATE_FILE = os.path.expanduser(
    "~/.kodi/userdata/weather_location_state.txt"
)

is_live = False

if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, "r") as f:
            is_live = (f.read().strip() == "live")
    except Exception:
        pass

# Live-Modus:
# Den bereits laufenden Worker sofort zu einem Sync auffordern.
if is_live:
    try:
        subprocess.run(
            [
                "pkill",
                "-USR1",
                "-f",
                "live_sync_worker.py"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

# Radar außerhalb des Workers nur für den statischen Modus
# aktualisieren.
else:
    try:
        subprocess.run(
            [
                "/usr/bin/python3",
                "/home/pi/update_radar.py"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception:
        pass
