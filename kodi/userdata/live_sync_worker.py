#!/usr/bin/env python3
import os
import sys
import subprocess
import xml.etree.ElementTree as ET
import urllib.request
import base64
import json
import time

STATE_FILE = os.path.expanduser("~/.kodi/userdata/weather_location_state.txt")
SETTINGS_MULTI = os.path.expanduser("~/.kodi/userdata/addon_data/weather.multi/settings.xml")
AUTH_HEADER = "Basic " + base64.b64encode(b"kodi:1998").decode()

RADAR_A = "/home/pi/.kodi/userdata/radar_live_a.png"
RADAR_B = "/home/pi/.kodi/userdata/radar_live_b.png"
CURRENT_SLOT_FILE = "/home/pi/.kodi/userdata/.radar_current_slot"

sys.path.append(os.path.expanduser("~/.kodi/userdata"))
from gps_nmea_provider import get_live_gps, resolve_location_schema

def kodi_rpc(method, params):
    url = "http://127.0.0.1:8080/jsonrpc"
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": AUTH_HEADER}
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.read().decode()
    except Exception:
        return None

def kodi_cmd(action_str):
    return kodi_rpc("Addons.ExecuteAddon", {
        "addonid": "script.service.audi.cmd",
        "params": [action_str]
    })

def get_next_radar_target():
    slot = "a"
    if os.path.exists(CURRENT_SLOT_FILE):
        try:
            with open(CURRENT_SLOT_FILE, "r") as f:
                if f.read().strip() == "a":
                    slot = "b"
        except Exception:
            pass
    with open(CURRENT_SLOT_FILE, "w") as f:
        f.write(slot)
    return RADAR_A if slot == "a" else RADAR_B

def run_sync():
    if not os.path.exists(STATE_FILE):
        return
    with open(STATE_FILE, "r") as f:
        if f.read().strip() != "live":
            return

    coords = get_live_gps()
    if not coords:
        print("[WORKER] Kein GPS empfangen.")
        return

    lat, lon = coords
    town, full_name, url, woeid = resolve_location_schema(lat, lon)

    print(f"[WORKER] Live-Standort: {full_name} ({lat}, {lon})")
    print(f"[WORKER] Yahoo-URL:     {url}")
    print(f"[WORKER] WOEID:         {woeid}")

    # 1. MultiWeather XML aktualisieren
    if os.path.exists(SETTINGS_MULTI):
        try:
            tree = ET.parse(SETTINGS_MULTI)
            root = tree.getroot()
            for s in root.findall("setting"):
                sid = s.get("id")
                if sid == "loc2_name": s.text = str(full_name)
                elif sid == "loc2_url": s.text = str(url)
                elif sid == "loc2_lat": s.text = str(lat)
                elif sid == "loc2_lon": s.text = str(lon)
                elif sid == "loc2_id": s.text = str(woeid)
            tree.write(SETTINGS_MULTI, encoding="utf-8", xml_declaration=True)
            print("[WORKER] Settings.xml geschrieben.")
        except Exception as e:
            print(f"[WORKER] XML-Fehler: {e}")

    # 2. A/B Radar Rendering
    radar_target = get_next_radar_target()
    try:
        res = subprocess.run([
            "/usr/bin/python3", "/home/pi/update_radar.py",
            "--lat", str(lat),
            "--lon", str(lon),
            "--file", radar_target
        ], capture_output=True, text=True, timeout=15)
        if res.returncode != 0:
            print(f"[WORKER] Radar Renderfehler: {res.stderr}")
        else:
            print(f"[WORKER] Radar gerendert nach: {radar_target}")
    except Exception as e:
        print(f"[WORKER] Radar Subprocess Fehler: {e}")

    # 3. Kodi UI und Properties via Dispatcher setzen
    ts = int(time.time())
    kodi_cmd("Skin.SetString(WeatherLocationMode,live)")
    kodi_cmd(f'Skin.SetString(WeatherLiveLocationName,"{full_name}")')
    kodi_cmd(f"Skin.SetString(WeatherRadarLivePath,{radar_target})")
    kodi_cmd(f"Skin.SetString(RadarTimestamp,{ts})")
    kodi_cmd("Weather.LocationSet(2)")

    # 4. weather.multi aufrufen
    kodi_rpc("Addons.ExecuteAddon", {"addonid": "weather.multi", "params": ["2"]})

    # 5. UI Refresh
    kodi_cmd("Container.Refresh")
    kodi_rpc("GUI.ShowNotification", {"title": "Live-Wetter", "message": full_name, "displaytime": 3000})
    print("[WORKER] Sync-Durchlauf abgeschlossen.")

if __name__ == "__main__":
    while True:
        try:
            run_sync()
        except Exception as e:
            print(f"[LOOP ERROR] {e}")
        time.sleep(120)
