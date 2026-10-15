import urllib.request
import json
import os
import sys

TARGET_PATH = os.path.expanduser("~/.kodi/userdata/weather_radar.png")

def update_radar():
    try:
        # RainViewer API fuer die aktuellste Radar-Ebene
        api_url = "https://api.rainviewer.com/public/weather-maps.json"
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            
        host = data.get("host")
        # Neuesten Radar-Timestamp holen
        past_frames = data.get("radar", {}).get("past", [])
        if not past_frames:
            return
        latest_path = past_frames[-1].get("path")
        
        # Koordinaten Kleve Zoom Level 7 (Tile x=66, y=42)
        # Direktes Tile fuer NRW / Niederrhein
        img_url = f"{host}{latest_path}/256/7/66/42/2/1_1.png"
        
        urllib.request.urlretrieve(img_url, TARGET_PATH + ".tmp")
        os.replace(TARGET_PATH + ".tmp", TARGET_PATH)
    except Exception as e:
        pass

if __name__ == "__main__":
    update_radar()
