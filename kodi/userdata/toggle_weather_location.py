import xbmc
import xbmcaddon
import socket
import subprocess
import re
import os
import json
import urllib.request
import urllib.parse
import ssl
import xml.etree.ElementTree as ET

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

S24_MAC = "F4:2B:8C:23:CD:78"
STATE_FILE = os.path.expanduser("~/.kodi/userdata/weather_location_state.txt")
SETTINGS_MULTI = os.path.expanduser("~/.kodi/userdata/addon_data/weather.multi/settings.xml")

def notify(msg):
    xbmc.executebuiltin(f"Notification(Wetter-Standort, {msg}, 3000)")

def get_live_gps(mac=S24_MAC):
    channel = 6
    try:
        sdp = subprocess.check_output(f"sdptool search --bdaddr {mac} SP", shell=True, timeout=2).decode()
        m = re.search(r"Channel:\s+(\d+)", sdp)
        if m: channel = int(m.group(1))
    except Exception:
        pass

    s = None
    try:
        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        s.settimeout(3.5)
        s.connect((mac, channel))
        buf = ""
        for _ in range(35):
            chunk = s.recv(1024).decode("ascii", errors="replace")
            buf += chunk
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if line.startswith(("$GNGGA", "$GPGGA")):
                    p = line.split(",")
                    if len(p) > 5 and p[2] and p[4]:
                        raw_lat, lat_dir = float(p[2]), p[3]
                        raw_lon, lon_dir = float(p[4]), p[5]
                        lat = (int(raw_lat / 100)) + (raw_lat % 100) / 60.0
                        if lat_dir == 'S': lat = -lat
                        lon = (int(raw_lon / 100)) + (raw_lon % 100) / 60.0
                        if lon_dir == 'W': lon = -lon
                        return round(lat, 4), round(lon, 4)
    except Exception:
        pass
    finally:
        if s:
            try: s.close()
            except Exception: pass
    return None

def resolve_location_schema(lat, lon):
    town = "Frankfurt"
    region = "HE"
    country = "DE"
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10"
        req = urllib.request.Request(url, headers={'User-Agent': 'AudiRpiAutomotive/1.0'})
        with urllib.request.urlopen(req, timeout=3, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            addr = data.get("address", {})
            town = addr.get("city") or addr.get("town") or addr.get("municipality") or addr.get("village") or "Unbekannt"
            region = addr.get("state") or addr.get("county") or "NW"
            country = addr.get("country_code", "de").upper()
    except Exception:
        pass

    # MultiWeather URL- und Namens-Schema
    clean_town = town.lower().replace(' ', '-')
    clean_region = region.lower().replace(' ', '-')
    clean_country = country.lower().replace(' ', '-')
    
    url = f"{clean_country}/{clean_region}/{clean_town}"
    name = f"{town}, {region}, {country}"
    woeid = 2934246 # Valide Ganzzahl-ID

    return town, name, url, woeid

is_live = False
if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, "r") as f:
            is_live = (f.read().strip() == "live")
    except Exception:
        pass

if not is_live:
    # Modus: LIVE
    notify("Live-GPS wird abgefragt...")
    coords = get_live_gps()
    if not coords:
        notify("Kein GPS-Fix vom S24!")
        exit(0)

    lat, lon = coords
    town, full_name, url, woeid = resolve_location_schema(lat, lon)

    # 1. MultiWeather Settings nativ über Kodi Addon-API setzen
    try:
        mw = xbmcaddon.Addon("weather.multi")
        mw.setSettingString("loc2_name", full_name)
        mw.setSettingString("loc2_url", url)
        mw.setSettingNumber("loc2_lat", float(lat))
        mw.setSettingNumber("loc2_lon", float(lon))
        mw.setSettingInt("loc2_id", int(woeid))
    except Exception as e:
        pass

    # 2. settings.xml auf Disk absichern
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
        except Exception:
            pass

    with open(STATE_FILE, "w") as f:
        f.write("live")

    # 3. Kodi GUI aktualisieren
    xbmc.executebuiltin("Skin.SetString(WeatherLocationMode,live)")
    xbmc.executebuiltin(f"Skin.SetString(WeatherLiveLocationName,{full_name})")
    xbmc.executebuiltin("Weather.LocationSet(2)")
    xbmc.executebuiltin("SetProperty(RadarFile,/home/pi/.kodi/userdata/radar.png,Weather)")
    xbmc.executebuiltin('RunScript(weather.multi,2)')
    notify(f"Aktiv: {full_name}")
else:
    # Modus: KLEVE
    with open(STATE_FILE, "w") as f:
        f.write("kleve")

    xbmc.executebuiltin("Skin.SetString(WeatherLocationMode,kleve)")
    xbmc.executebuiltin("Skin.SetString(WeatherLiveLocationName,Kleve)")
    xbmc.executebuiltin("Weather.LocationSet(1)")
    xbmc.executebuiltin("SetProperty(RadarFile,/home/pi/.kodi/userdata/radar.png,Weather)")
    xbmc.executebuiltin('RunScript(weather.multi,1)')
    notify("Aktiv: Kleve")

# Radar im Hintergrund anstossen
subprocess.Popen(["/usr/bin/python3", "/home/pi/update_radar.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
