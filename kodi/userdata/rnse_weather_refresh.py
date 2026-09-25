#!/usr/bin/env python3

import os
import subprocess
import xbmc

STATE_FILE = os.path.expanduser(
    "~/.kodi/userdata/weather_location_state.txt"
)

mode = "kleve"

try:
    with open(STATE_FILE, "r") as f:
        mode = f.read().strip()
except Exception:
    pass

if mode == "live":
    # Live-/Mock-GPS:
    # Worker sofort aufwecken. Er liest den aktuellen Standort,
    # schreibt weather.multi neu, aktualisiert Wetter und Radar.
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

    xbmc.executebuiltin(
        'Notification(Wetter,"Live-Standort wird aktualisiert...",2000)'
    )

else:
    # Statischer Kleve-Modus
    xbmc.executebuiltin("Weather.LocationSet(1)")
    xbmc.executebuiltin("RunScript(weather.multi,1)")

    subprocess.Popen(
        [
            "/usr/bin/python3",
            "/home/pi/update_radar.py",
            "--lat",
            "51.7904",
            "--lon",
            "6.13777",
            "--file",
            "/home/pi/.kodi/userdata/radar_1.png"
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    xbmc.executebuiltin(
        'Notification(Wetter,"Wetter wird aktualisiert...",2000)'
    )
