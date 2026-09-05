#!/usr/bin/env python3
import time
import os
import sys
import json
import urllib.request
import subprocess
import signal
import threading
import xml.etree.ElementTree as ET

sys.path.append(os.path.expanduser("~/.kodi/userdata"))
from gps_nmea_provider import get_live_gps, resolve_location_schema

STATE_FILE = os.path.expanduser("~/.kodi/userdata/weather_location_state.txt")
SETTINGS_MULTI = os.path.expanduser("~/.kodi/userdata/addon_data/weather.multi/settings.xml")
RADAR_IDX_FILE = os.path.expanduser("~/.kodi/userdata/radar_idx.txt")
KODI_JSON_URL = "http://127.0.0.1:8080/jsonrpc"
KODI_USER = "kodi"
KODI_PASS = "1998"

sync_trigger_event = threading.Event()

def handle_sigusr1(signum, frame):
    print("[WORKER] Sofortiger Ad-hoc-Sync via SIGUSR1 getriggert.", flush=True)
    sync_trigger_event.set()

def kodi_rpc(method, params=None):
    payload = {"jsonrpc": "2.0", "method": method, "id": 1}
    if params:
        payload["params"] = params
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(KODI_JSON_URL, data=data, headers={"Content-Type": "application/json"})
    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, KODI_JSON_URL, KODI_USER, KODI_PASS)
    handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
    opener = urllib.request.build_opener(handler)
    try:
        with opener.open(req, timeout=3) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"[WORKER] RPC Fehler bei {method}: {e}", flush=True)
        return None

def kodi_cmd(builtin):
    return kodi_rpc("Addons.ExecuteAddon", {"addonid": "script.service.audi.cmd", "params": [builtin]})

def get_next_radar_slot():
    slot_char = "a"
    if os.path.exists(RADAR_IDX_FILE):
        try:
            with open(RADAR_IDX_FILE, "r") as f:
                cur = f.read().strip()
                slot_char = "b" if cur == "a" else "a"
        except Exception:
            slot_char = "a"
    with open(RADAR_IDX_FILE, "w") as f:
        f.write(slot_char)
    next_idx = 1 if slot_char == "b" else 0
    return f"/home/pi/.kodi/userdata/radar_live_{slot_char}.png", next_idx

def run_sync():
    # 1. State prüfen
    is_live = True
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                is_live = (f.read().strip() == "live")
        except Exception:
            is_live = True

    if not is_live:
        print("[WORKER] Modus steht auf kleve - kein Live-Sync erforderlich.", flush=True)
        return

    coords = get_live_gps()
    if not coords:
        print("[WORKER] Kein GPS empfangen.", flush=True)
        return

    lat, lon = coords
    town, full_name, url, woeid = resolve_location_schema(lat, lon)
    print(f"[WORKER] Live-Standort: {full_name} ({lat}, {lon})", flush=True)

    # settings.xml aktualisieren (Slot 2)
    if os.path.exists(SETTINGS_MULTI):
        try:
            tree = ET.parse(SETTINGS_MULTI)
            root = tree.getroot()
            for s in root.findall("setting"):
                sid = s.get("id")
                if sid == "loc2_name": s.text = full_name
                elif sid == "loc2_url": s.text = url
                elif sid == "loc2_lat": s.text = str(lat)
                elif sid == "loc2_lon": s.text = str(lon)
                elif sid == "loc2_id": s.text = str(woeid)
            tree.write(SETTINGS_MULTI, encoding="utf-8", xml_declaration=True)
            print("[WORKER] Settings.xml geschrieben.", flush=True)
        except Exception as e:
            print(f"[WORKER] Fehler beim Schreiben der settings.xml: {e}", flush=True)

    # 2. A/B Radar zentriert rendern
    radar_target, slot_idx = get_next_radar_slot()
    try:
        cmd = ["/usr/bin/python3", "/home/pi/update_radar.py", "--lat", str(lat), "--lon", str(lon), "--file", radar_target]
        subprocess.run(cmd, timeout=30, check=True)
        print(f"[WORKER] Radar gerendert nach: {radar_target}", flush=True)
    except Exception as e:
        print(f"[WORKER] Radar Subprocess Fehler: {e}", flush=True)

    # 3. Kodi UI und Properties via Dispatcher setzen
    ts = int(time.time())
    kodi_cmd("Skin.SetString(WeatherLocationMode,live)")
    kodi_cmd(f'Skin.SetString(WeatherLiveLocationName,"{full_name}")')
    kodi_cmd(f"Skin.SetString(WeatherRadarLivePath,{radar_target})")
    kodi_cmd(f"Skin.SetString(RadarTimestamp,{ts})")
    kodi_cmd("Weather.LocationSet(2)")

    # 4. weather.multi abrufen
    kodi_rpc("Addons.ExecuteAddon", {"addonid": "weather.multi", "params": ["2"]})

    # 5. UI Refresh
    kodi_cmd("Container.Refresh")
    kodi_rpc("GUI.ShowNotification", {"title": "Live-Wetter", "message": full_name, "displaytime": 3000})
    print("[WORKER] Sync-Durchlauf abgeschlossen.", flush=True)

if __name__ == "__main__":
    signal.signal(signal.SIGUSR1, handle_sigusr1)
    while True:
        try:
            run_sync()
        except Exception as e:
            print(f"[LOOP ERROR] {e}", flush=True)
        sync_trigger_event.wait(timeout=120)
        sync_trigger_event.clear()
