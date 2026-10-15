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
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (AudiRpiAutomotive/3.0)'})
    with urllib.request.urlopen(req, timeout=4, context=ctx) as resp:
        return Image.open(io.BytesIO(resp.read())).convert("RGBA")

def build_radar(lat, lon, target_file):
    xtile, ytile, x_off, y_off = deg2num(lat, lon, ZOOM_LEVEL)

    # 1. RainViewer API abfragen fuer aktuellen Frame
    radar_host = None
    frame_path = None
    try:
        api_url = "https://api.rainviewer.com/public/weather-maps.json"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0 (AudiRpiAutomotive/3.0)'})
        with urllib.request.urlopen(req, timeout=4, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            radar_host = data["host"]
            frame_path = data["radar"]["past"][-1]["path"]
    except Exception:
        pass

    # 2. 3x3 Canvas initialisieren (3 * 256 = 768x768)
    stitched_map = Image.new("RGBA", (768, 768), (35, 35, 35, 255))
    stitched_radar = Image.new("RGBA", (768, 768), (0, 0, 0, 0))

    # 3. 3x3 Kacheln herunterladen und zusammenfuegen (-1 bis +1 um Zentrum)
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            cur_x = xtile + dx
            cur_y = ytile + dy
            pos_x = (dx + 1) * 256
            pos_y = (dy + 1) * 256

            # OSM Kachel
            osm_urls = [
                f"https://tile.openstreetmap.de/{ZOOM_LEVEL}/{cur_x}/{cur_y}.png",
                f"https://tile.openstreetmap.org/{ZOOM_LEVEL}/{cur_x}/{cur_y}.png"
            ]
            for u in osm_urls:
                try:
                    tile_img = download_image(u)
                    stitched_map.paste(tile_img, (pos_x, pos_y))
                    break
                except Exception:
                    continue

            # RainViewer Kachel
            if radar_host and frame_path:
                r_url = f"{radar_host}{frame_path}/256/{ZOOM_LEVEL}/{cur_x}/{cur_y}/2/1_1.png"
                try:
                    r_img = download_image(r_url)
                    center_px = r_img.getpixel((128, 128))
                    if not (center_px[0] > 180 and center_px[1] < 50):
                        stitched_radar.paste(r_img, (pos_x, pos_y))
                except Exception:
                    pass

    # 4. Karten & Radar vereinen
    full_composite = Image.alpha_composite(stitched_map, stitched_radar)

    # 5. Perfektes Center-Cropping auf 512x512
    # Der GPS-Punkt liegt auf der zentralen Kachel bei (256 + x_off*256, 256 + y_off*256)
    center_x = 256.0 + (x_off * 256.0)
    center_y = 256.0 + (y_off * 256.0)

    crop_left = int(round(center_x - 256.0))
    crop_top = int(round(center_y - 256.0))
    crop_right = crop_left + 512
    crop_bottom = crop_top + 512

    # Bild zuschneiden (Standort liegt exakt im Zentrum bei 256, 256)
    final_image = full_composite.crop((crop_left, crop_top, crop_right, crop_bottom))

    # 6. Roter Standort-Pin (Audi OEM Style) exakt in der Bildmitte
    draw = ImageDraw.Draw(final_image)
    px, py = 256, 256
    r = 7
    draw.ellipse((px - r - 2, py - r - 2, px + r + 2, py + r + 2), fill=(255, 255, 255, 230))
    draw.ellipse((px - r, py - r, px + r, py + r), fill=(220, 0, 0, 255))
    draw.ellipse((px - 2, py - 2, px + 2, py + 2), fill=(255, 255, 255, 255))

    # 7. Speichern
    final_image.save(target_file, "PNG")
    try:
        final_image.save("/home/pi/.kodi/userdata/radar.png", "PNG")
    except Exception:
        pass

    print(f"Radar erfolgreich zentriert erstellt in {target_file} fuer Lat {lat}, Lon {lon}")

def resolve_target_and_coords():
    is_live = False
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                if f.read().strip() == "live":
                    is_live = True
        except Exception:
            pass

    target_file = "/home/pi/.kodi/userdata/radar_2.png" if is_live else "/home/pi/.kodi/userdata/radar_1.png"
    target_loc_id = "loc2" if is_live else "loc1"

    lat = 51.7904
    lon = 6.13777
    if os.path.exists(SETTINGS_MULTI):
        try:
            tree = ET.parse(SETTINGS_MULTI)
            root = tree.getroot()
            for s in root.findall("setting"):
                if s.get("id") == f"{target_loc_id}_lat": lat = float(s.text)
                elif s.get("id") == f"{target_loc_id}_lon": lon = float(s.text)
        except Exception:
            pass
    return lat, lon, target_file

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, help="Latitude")
    parser.add_argument("--lon", type=float, help="Longitude")
    parser.add_argument("--file", type=str, help="Target PNG file")
    args = parser.parse_args()

    if args.lat is not None and args.lon is not None and args.file:
        lat, lon, target_file = args.lat, args.lon, args.file
    else:
        lat, lon, target_file = resolve_target_and_coords()

    build_radar(lat, lon, target_file)
