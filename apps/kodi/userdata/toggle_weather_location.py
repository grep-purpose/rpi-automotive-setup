#!/usr/bin/env python3
import os
import subprocess

STATE_FILE = os.path.expanduser("~/.kodi/userdata/weather_location_state.txt")

try:
    import xbmc
    def notify(msg): xbmc.executebuiltin(f'Notification(Wetter-Standort, "{msg}", 2500)')
    def run_builtin(cmd): xbmc.executebuiltin(cmd)
except ImportError:
    def notify(msg): print(f"[NOTIFY] {msg}")
    def run_builtin(cmd): print(f"[CMD] {cmd}")

is_live = False
if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, "r") as f:
            is_live = (f.read().strip() == "live")
    except Exception:
        pass

if not is_live:
    # Umschalten auf LIVE
    with open(STATE_FILE, "w") as f:
        f.write("live")

    run_builtin("Skin.SetString(WeatherLocationMode,live)")
    run_builtin("Weather.LocationSet(2)")
    notify("Live-GPS Sync angefordert...")

    # Worker via SIGUSR1 sofort aufwecken
    subprocess.run(["pkill", "-USR1", "-f", "live_sync_worker.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
else:
    # Umschalten auf KLEVE
    with open(STATE_FILE, "w") as f:
        f.write("kleve")

    run_builtin("Skin.SetString(WeatherLocationMode,kleve)")
    run_builtin('Skin.SetString(WeatherLiveLocationName,"Kleve, NRW, DE")')
    run_builtin("Weather.LocationSet(1)")
    run_builtin("RunScript(weather.multi,1)")
    notify("Aktiv: Kleve, NRW, DE")

    # Radar fuer Kleve anstossen
    subprocess.Popen(["/usr/bin/python3", "/home/pi/update_radar.py", "--lat", "51.7904", "--lon", "6.13777", "--file", "/home/pi/.kodi/userdata/radar_1.png"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
