#!/usr/bin/env python3
import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
import os
import ssl
import time
import gzip
import re

PORT = 8088
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

class WaipuAuth:
    def __init__(self):
        self.access_token = None
        self.device_token = None
        self.token_expiry = 0
        self.stream_cache = {}
        self.load_credentials()

    def load_credentials(self):
        settings_path = os.path.expanduser("~/.kodi/userdata/addon_data/pvr.waipu/settings.xml")
        self.dev_id = "cd8c2238-4e43-481b-8665-472ae21ae816"
        self.refresh_token = ""
        if os.path.exists(settings_path):
            tree = ET.parse(settings_path)
            for s in tree.getroot().findall("setting"):
                if s.get("id") == "device_id_uuid4":
                    self.dev_id = s.text
                elif s.get("id") == "refresh_token":
                    self.refresh_token = s.text

    def refresh(self):
        if self.access_token and self.device_token and time.time() < (self.token_expiry - 120):
            return
        self.load_credentials()
        
        token_url = "https://auth.waipu.tv/oauth/token"
        payload = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": "waipu",
            "waipu_device_id": self.dev_id
        }).encode("utf-8")
        req_t = urllib.request.Request(token_url, data=payload, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "okhttp/4.9.0",
            "Accept": "application/json"
        })
        with urllib.request.urlopen(req_t, context=ctx) as r:
            data = json.loads(r.read().decode("utf-8"))
            self.access_token = data.get("access_token")
            self.token_expiry = time.time() + data.get("expires_in", 3600)

        dc_url = "https://device-capabilities.waipu.tv/api/device-capabilities"
        dc_body = {
            "appVersion": "WEB_CLIENT@4.48.0",
            "type": "web",
            "platform": "Linux",
            "manufacturer": "",
            "model": ""
        }
        req_dc = urllib.request.Request(dc_url, data=json.dumps(dc_body).encode("utf-8"), headers={
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/vnd.dc.device-info-v1+json",
            "Accept": "application/vnd.dc.device-capabilities-v1+json, application/json, */*",
            "User-Agent": "Mozilla/5.0"
        }, method="POST")
        with urllib.request.urlopen(req_dc, context=ctx) as r_dc:
            self.device_token = json.loads(r_dc.read().decode("utf-8")).get("token")

    def fetch_decompressed(self, url):
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Encoding": "gzip",
            "Accept": "*/*"
        })
        with urllib.request.urlopen(req, context=ctx) as r:
            data = r.read()
            if r.info().get("Content-Encoding") == "gzip" or (len(data) >= 2 and data[:2] == b"\x1f\x8b"):
                return gzip.decompress(data).decode("utf-8")
            return data.decode("utf-8")

    def get_stream_url(self, station_id):
        self.refresh()
        now = time.time()
        if station_id in self.stream_cache:
            stream_url, exp = self.stream_cache[station_id]
            if now < (exp - 300):
                return stream_url

        url = "https://stream-url-provider.waipu.tv/api/stream-url"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/vnd.streamurlprovider.stream-url-request-v1+json",
            "Accept": "application/vnd.streamurlprovider.traditional-stream-url-v1+json",
            "X-Device-Token": self.device_token,
            "User-Agent": "Mozilla/5.0"
        }
        body = {
            "stream": {"station": station_id, "protocol": "hls", "requestMuxInstrumentation": True, "processOutcomeField": True},
            "advertising": {"id": "00000000-0000-0000-0000-000000000000", "gdprConsent": "", "serverSideAdInsertion": True}
        }
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, context=ctx) as r:
            res = json.loads(r.read().decode("utf-8"))
            stream_url = res.get("streamUrl")
            exp = res.get("tokenExpiresAt", now + 14400)
            self.stream_cache[station_id] = (stream_url, exp)
            return stream_url

waipu_auth = WaipuAuth()

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path.startswith("/live/"):
                station_id = self.path.split("/live/")[1].split("?")[0].replace(".m3u8", "")
                target_url = waipu_auth.get_stream_url(station_id)
                raw_manifest = waipu_auth.fetch_decompressed(target_url)
                base_cdn_url = target_url.rsplit("/", 1)[0] + "/"
                
                filtered_lines = []
                skip_next_url = False
                
                for line in raw_manifest.splitlines():
                    sl = line.strip()
                    if not sl:
                        continue
                    
                    if sl.startswith("#EXT-X-STREAM-INF"):
                        # Filtere 1080p und hohe Bitraten heraus (optimal für RNS-E Scaler)
                        if "1920x1080" in sl or "BANDWIDTH=7000000" in sl or "BANDWIDTH=6000000" in sl:
                            skip_next_url = True
                            continue
                        else:
                            skip_next_url = False
                    elif skip_next_url and not sl.startswith("#"):
                        skip_next_url = False
                        continue
                    
                    if not sl.startswith("#"):
                        full_sub = urllib.parse.urljoin(base_cdn_url, sl) if not sl.startswith("http") else sl
                        encoded = urllib.parse.quote(full_sub)
                        sl = f"http://127.0.0.1:8088/sub?u={encoded}"
                    
                    filtered_lines.append(sl)

                resp = "\n".join(filtered_lines).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)

            elif self.path.startswith("/sub?u="):
                target_url = urllib.parse.unquote(self.path.split("/sub?u=")[1])
                raw_sub = waipu_auth.fetch_decompressed(target_url)
                sub_base = target_url.rsplit("/", 1)[0] + "/"

                rewritten_sub = []
                for line in raw_sub.splitlines():
                    sl = line.strip()
                    if not sl:
                        continue
                    if not sl.startswith("#"):
                        if not sl.startswith("http"):
                            sl = urllib.parse.urljoin(sub_base, sl)
                    rewritten_sub.append(sl)

                resp = "\n".join(rewritten_sub).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.apple.mpegurl")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)

            else:
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()

        except Exception as e:
            err_msg = str(e).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(err_msg)))
            self.end_headers()
            self.wfile.write(err_msg)

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/vnd.apple.mpegurl")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def log_message(self, format, *args):
        pass

class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    with ReusableTCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()
