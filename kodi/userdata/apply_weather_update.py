import xbmc
import json
import os

STATE_FILE = os.path.expanduser("~/.kodi/userdata/weather_location_state.txt")
STATUS_FILE = os.path.expanduser("~/.kodi/userdata/radar_status.json")

if os.path.exists(STATUS_FILE):
    try:
        with open(STATUS_FILE, "r") as f:
            data = json.load(f)
        city = data.get("city", "Live-Standort")
        xbmc.executebuiltin(f"Skin.SetString(WeatherLiveLocationName,{city})")
        xbmc.executebuiltin("Weather.LocationSet(2)")
        xbmc.executebuiltin("Weather.Refresh")
        xbmc.executebuiltin(f"Notification(Standort aktualisiert,{city},3000)")
    except Exception as e:
        pass
