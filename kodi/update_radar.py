#!/usr/bin/env python3
import math
import os
import io
import urllib.request
import json
import ssl
import argparse
import time
import subprocess
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

ZOOM_LEVEL = 7
STATE_FILE = os.path.expanduser("~/.kodi/userdata/weather_location_state.txt")
SETTINGS_MULTI = os.path.expanduser("~/.kodi/userdata/addon_data/weather.multi/settings.xml")

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = (lon_deg + 180.0) / 360.0 * n
    ytile = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return int(xtile), int(ytile), xtile - int(xtile), ytile - int(ytile)

def download_image(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (AudiRpiAutomotive/1.0)'})
    with urllib.request.urlopen(req, timeout=4, context=ctx) as resp:
        return Image.open(io.BytesIO(resp.read())).convert("RGBA")

def build_radar(lat, lon, target_file):
    xtile, ytile, x_off, y_off = deg2num(lat, lon, ZOOM_LEVEL)

    # 1. Basiskarte (OpenStreetMap DE)
    base_url = f"https://tile.openstreetmap.de/{ZOOM_LEVEL}/{xtile}/{ytile}.png"
    try:
        base_map = download_image(base_url).resize((512, 512), Image.Resampling.BICUBIC)
    except Exception:
        try:
            osm_url = f"https://tile.openstreetmap.org/{ZOOM_LEVEL}/{xtile}/{ytile}.png"
            base_map = download_image(osm_url).resize((512, 512), Image.Resampling.BICUBIC)
        except Exception:
            base_map = Image.new("RGBA", (512, 512), (35, 35, 35, 255))

    # 2. RainViewer Kachel
    radar_layer = None
    try:
        api_url = "https://api.rainviewer.com/public/weather-maps.json"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0 (AudiRpiAutomotive/1.0)'})
        with urllib.request.urlopen(req, timeout=4, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            host = data["host"]
            past = data["radar"]["past"]
            frame_path = past[-1]["path"]
            tile_url = f"{host}{frame_path}/256/{ZOOM_LEVEL}/{xtile}/{ytile}/2/1_1.png"
            img = download_image(tile_url)
            center_pixel = img.getpixel((128, 128))
            if not (center_pixel[0] > 180 and center_pixel[1] < 50):
                radar_layer = img.resize((512, 512), Image.Resampling.NEAREST)
    except Exception:
        pass

    # 3. Layer kombinieren
    if radar_layer:
        composite = Image.alpha_composite(base_map, radar_layer)
    else:
        composite = base_map

    # 4. Roter Standort-Pin (Audi OEM Style)
    draw = ImageDraw.Draw(composite)
    px = int(x_off * 512)
    py = int(y_off * 512)
    r = 7
    draw.ellipse((px - r - 2, py - r - 2, px + r + 2, py + r + 2), fill=(255, 255, 255, 230))
    draw.ellipse((px - r, py - r, px + r, py + r), fill=(220, 0, 0, 255))
    draw.ellipse((px - 2, py - 2, px + 2, py + 2), fill=(255, 255, 255, 255))

    # 5. Speichern
    composite.save(target_file, "PNG")
    # Auch Default-Datei aktualisieren
    composite.save("/home/pi/.kodi/userdata/radar.png", "PNG")
    print(f"Radar erfolgreich erstellt in {target_file} fuer Lat {lat}, Lon {lon}")

    # Kodi mitteilen, dass ein neues Bild vorliegt (Timestamp fuer Cache-Bypass)
    try:
        ts = int(time.time())
        subprocess.run(["kodi-send", f"--action=Skin.SetString(RadarTimestamp,{ts})"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def resolve_target_and_coords():
    is_live = False
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                is_live = (f.read().strip() == "live")
        except Exception:
            pass

    if is_live and os.path.exists(SETTINGS_MULTI):
        try:
            tree = ET.parse(SETTINGS_MULTI)
            root = tree.getroot()
            lat, lon = None, None
            for s in root.findall("setting"):
                sid = s.get("id")
                if sid == "loc2_lat":
                    lat = float(s.text)
                elif sid == "loc2_lon":
                    lon = float(s.text)
            if lat is not None and lon is not None:
                print(f"[RADAR] Modus LIVE aktiv: {lat}, {lon}")
                return "/home/pi/.kodi/userdata/radar_2.png", lat, lon
        except Exception as e:
            print(f"[RADAR] Fehler bei loc2-Koordinaten: {e}")

    print("[RADAR] Modus KLEVE aktiv: 51.7883, 6.1389")
    return "/home/pi/.kodi/userdata/radar_1.png", 51.7883, 6.1389

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, default=None)
    parser.add_argument("--lon", type=float, default=None)
    parser.add_argument("--file", type=str, default=None)
    args = parser.parse_args()

    if args.lat is not None and args.lon is not None:
        target = args.file if args.file else "/home/pi/.kodi/userdata/radar.png"
        build_radar(args.lat, args.lon, target)
    else:
        target, active_lat, active_lon = resolve_target_and_coords()
        build_radar(active_lat, active_lon, target)
