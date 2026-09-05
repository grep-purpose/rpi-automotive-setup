#!/usr/bin/env python3
import math
import os
import io
import urllib.request
import json
import ssl
import argparse
from PIL import Image, ImageDraw

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

ZOOM_LEVEL = 7

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

def build_radar(lat, lon):
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
        req = urllib.request.Request("https://api.rainviewer.com/public/weather-maps.json", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4, context=ctx) as resp:
            data = json.loads(resp.read().decode())
        
        host = data.get("host", "https://tilecache.rainviewer.com")
        past = data.get("radar", {}).get("past", [])
        if past:
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

    # 4. Roter Standort-Pin
    draw = ImageDraw.Draw(composite)
    px = int(x_off * 512)
    py = int(y_off * 512)
    r = 7
    draw.ellipse((px - r - 2, py - r - 2, px + r + 2, py + r + 2), fill=(255, 255, 255, 230))
    draw.ellipse((px - r, py - r, px + r, py + r), fill=(220, 0, 0, 255))
    draw.ellipse((px - 2, py - 2, px + 2, py + 2), fill=(255, 255, 255, 255))

    # 5. Speichern
    target = "/home/pi/.kodi/userdata/radar.png"
    composite.save(target, "PNG")
    print(f"Radar erfolgreich erstellt fuer Lat {lat}, Lon {lon}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, default=51.7883)
    parser.add_argument("--lon", type=float, default=6.1389)
    args = parser.parse_args()
    build_radar(args.lat, args.lon)
