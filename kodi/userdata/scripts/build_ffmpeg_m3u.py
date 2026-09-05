import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
import os
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

settings_path = os.path.expanduser("~/.kodi/userdata/addon_data/pvr.waipu/settings.xml")
dev_id, token = "cd8c2238-4e43-481b-8665-472ae21ae816", ""
if os.path.exists(settings_path):
    tree = ET.parse(settings_path)
    for s in tree.getroot().findall("setting"):
        if s.get("id") == "device_id_uuid4": dev_id = s.text
        elif s.get("id") == "refresh_token": token = s.text

token_url = "https://auth.waipu.tv/oauth/token"
payload = urllib.parse.urlencode({
    "grant_type": "refresh_token",
    "refresh_token": token,
    "client_id": "waipu",
    "waipu_device_id": dev_id
}).encode("utf-8")

req_t = urllib.request.Request(token_url, data=payload, headers={
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "okhttp/4.9.0",
    "Accept": "application/json"
})
with urllib.request.urlopen(req_t, context=ctx) as resp:
    access_token = json.loads(resp.read().decode())["access_token"]

stations_url = "https://user-stations.waipu.tv/api/stations"
req = urllib.request.Request(stations_url, headers={
    "Authorization": f"Bearer {access_token}",
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/vnd.waipu.user-stations-stations.v1+json"
})
with urllib.request.urlopen(req, context=ctx) as r:
    stations = json.loads(r.read().decode("utf-8"))

m3u_file = "/home/pi/waipu.m3u8"
with open(m3u_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for st in stations:
        name = st.get("displayName") or st.get("name") or "Sender"
        sid = st.get("stationId") or st.get("id") or ""
        logo = f"https://images.wpstr.tv/channels/{sid}/logo_light.png"
        stream_url = f"http://127.0.0.1:8088/live/{sid}.m3u8"

        f.write(f'#EXTINF:-1 tvg-id="{sid}" tvg-name="{name}" tvg-logo="{logo}" group-title="Waipu.tv",{name}\n')
        f.write('#KODIPROP:inputstream=inputstream.ffmpegdirect\n')
        f.write('#KODIPROP:inputstream.ffmpegdirect.mime_type=application/vnd.apple.mpegurl\n')
        f.write('#KODIPROP:inputstream.ffmpegdirect.is_realtime_stream=true\n')
        f.write('#KODIPROP:inputstream.ffmpegdirect.stream_mode=timeshift\n')
        f.write(f'{stream_url}\n')

print(f"/home/pi/waipu.m3u8 aktualisiert!")
