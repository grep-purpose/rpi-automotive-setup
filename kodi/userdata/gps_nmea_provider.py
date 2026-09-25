#!/usr/bin/env python3
import socket
import subprocess
import re
import json
import urllib.request
import urllib.parse
import ssl
import time

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

S24_MAC = "F4:2B:8C:23:CD:78"
LCURL = 'https://weather.yahoo.com/_atmos/api/search-assist/locations?query=%s'
BROWSER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
HEADERS = {'User-Agent': BROWSER_AGENT, 'Accept': 'application/json'}

def parse_nmea_coord(raw, direction):
    if not raw or not direction:
        return None
    try:
        dot = raw.find('.')
        if dot < 2: return None
        deg = float(raw[:dot-2])
        mins = float(raw[dot-2:])
        val = deg + (mins / 60.0)
        if direction in ['S', 'W']: val = -val
        return round(val, 4)
    except Exception:
        return None

def get_live_gps(mac=S24_MAC):
    channel = 7
    try:
        sdp = subprocess.check_output(f"sdptool search --bdaddr {mac} SP", shell=True, timeout=3).decode()
        m = re.search(r"Channel:\s+(\d+)", sdp)
        if m: channel = int(m.group(1))
    except Exception:
        pass

    for attempt in range(2):
        s = None
        try:
            s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
            s.settimeout(6.0)
            s.connect((mac, channel))
            time.sleep(0.3)
            buf = ""
            for _ in range(50):
                chunk = s.recv(1024).decode("ascii", errors="replace")
                if not chunk: break
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line.startswith(("$GNGGA", "$GPGGA", "$GNRMC", "$GPRMC")):
                        parts = line.split(",")
                        if "GGA" in parts[0] and len(parts) > 5 and parts[2] and parts[4]:
                            lat = parse_nmea_coord(parts[2], parts[3])
                            lon = parse_nmea_coord(parts[4], parts[5])
                            if lat and lon: return (lat, lon)
                        elif "RMC" in parts[0] and len(parts) > 6 and parts[2] == 'A' and parts[3] and parts[5]:
                            lat = parse_nmea_coord(parts[3], parts[4])
                            lon = parse_nmea_coord(parts[5], parts[6])
                            if lat and lon: return (lat, lon)
        except Exception as e:
            if attempt == 0:
                time.sleep(1.0)
                continue
            print(f"[GPS] Fehler: {e}", flush=True)
        finally:
            if s:
                try: s.close()
                except Exception: pass
    return None

def resolve_location_schema(lat, lon):
    town = None
    region = None
    country_code = "de"
    country_name = "Deutschland"

    # 1. Reverse Geocoding via BigDataCloud (bevorzugt Deutsch)
    try:
        bdc_url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lon}&localityLanguage=de"
        req = urllib.request.Request(bdc_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=4, context=ctx) as r:
            data = json.loads(r.read().decode())
            town = data.get("city") or data.get("locality") or data.get("principalSubdivision")
            region = data.get("principalSubdivision")
            country_code = data.get("countryCode", "de").lower()
            country_name = (
                data.get("countryName")
                or country_code.upper()
            )
    except Exception as e:
        print(f"[GEO] BDC: {e}", flush=True)

    # Fallback Nominatim
    if not town:
        try:
            nom_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1&accept-language=de"
            req = urllib.request.Request(nom_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=4, context=ctx) as r:
                data = json.loads(r.read().decode())
                addr = data.get("address", {})
                town = addr.get("city") or addr.get("town") or addr.get("municipality") or addr.get("village")
                region = addr.get("state") or addr.get("county")
                country_code = addr.get("country_code", "de").lower()
                country_name = (
                    addr.get("country")
                    or country_code.upper()
                )
        except Exception as e:
            print(f"[GEO] Nominatim: {e}", flush=True)

    if not town:
        town = "Live-Standort"
        country_code = "de"

    c_code = country_code.upper()
    
    # Einheitliches Schema: Stadt, Region, LAND
    if region and region.lower() != town.lower():
        full_name = f"{town}, {region}, {c_code}"
    else:
        full_name = f"{town}, {c_code}"

    # Yahoo URL Fallback-Struktur
    clean_town = town.lower().replace(" ", "-")
    clean_region = (region or "").lower().replace(" ", "-")
    url_slug = f"{country_code.lower()}/{clean_region}/{clean_town}" if clean_region else f"{country_code.lower()}/{clean_town}"
    woeid = 0

    # 2. Yahoo Search Assist
    #
    # Yahoo Search Assist liefert gelegentlich gecachte/falsche
    # Ergebnisse. Deshalb:
    # - vollständigen Ortsnamen verwenden
    # - Cache-Buster anhängen
    # - nur passende Stadt/Land-Kombination akzeptieren
    # - niemals irgendeinen fremden ersten Treffer übernehmen

    import time

    yahoo_match_found = False

    # Für übersetzte Ortsnamen wie
    # "Lissabon" -> "Lisbon":
    # Ein nicht exakt gleich geschriebener Treffer muss zweimal
    # hintereinander mit derselben WOEID erscheinen.
    pending_woeid = None
    pending_count = 0

    for attempt in range(5):
        try:
            # Sichtbarer Name bleibt deutsch.
            # Yahoo bekommt lediglich intern eine eindeutigere Suche,
            # z.B. "Lissabon Portugal".
            # Yahoo Search Assist reagiert auf zusätzliche
            # Landes-/Regionsbegriffe teilweise sehr unzuverlässig.
            # Deshalb ausschließlich nach dem Ortsnamen suchen.
            search_text = town

            safe_query = urllib.parse.quote(search_text)

            # Cache-Buster, damit Yahoo/CDN nicht eine alte
            # Suchantwort eines vorherigen Ortes zurückliefert.
            cache_buster = int(time.time() * 1000)

            y_url = (
                (LCURL % safe_query)
                + f"&_rnse={cache_buster}_{attempt}"
            )

            y_req = urllib.request.Request(
                y_url,
                headers={
                    **HEADERS,
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache"
                }
            )

            with urllib.request.urlopen(
                y_req,
                timeout=5,
                context=ctx
            ) as resp:
                data = json.loads(
                    resp.read().decode()
                )

            suggestions = data.get("suggestions", [])

            wanted_town = town.strip().lower()
            wanted_country = country_code.strip().lower()

            best = None

            for suggestion in suggestions:
                loc = suggestion.get("location", {})

                candidate_town = (
                    loc.get("town", {})
                    .get("name", "")
                    .strip()
                    .lower()
                )

                candidate_country = (
                    loc.get("country", {})
                    .get("code", "")
                    .strip()
                    .lower()
                )

                # Land muss zwingend stimmen.
                if candidate_country != wanted_country:
                    continue

                # Exakter Ortsname + richtiges Land:
                # sofort akzeptieren.
                if candidate_town == wanted_town:
                    best = suggestion
                    break

                # Der Ortsname kann übersetzt sein:
                # Lissabon -> Lisbon, München -> Munich usw.
                # Solche Treffer akzeptieren wir nicht sofort,
                # sondern erst nach zwei identischen Ergebnissen.
                candidate_woeid = (
                    loc.get("town", {})
                    .get("woeid", 0)
                )

                if candidate_woeid:
                    if candidate_woeid == pending_woeid:
                        pending_count += 1
                    else:
                        pending_woeid = candidate_woeid
                        pending_count = 1

                    if pending_count >= 2:
                        best = suggestion
                        break

            if best is None:
                print(
                    f"[YAHOO] Versuch {attempt + 1}: "
                    f"kein passender Treffer fuer "
                    f"{full_name!r}",
                    flush=True
                )

                time.sleep(0.4)
                continue

            loc = best.get("location", {})

            yc_code = (
                loc.get("country", {})
                .get("code", country_code)
                .lower()
            )

            yr_name = (
                loc.get("region", {})
                .get("name", region or "")
                .lower()
                .replace(" ", "-")
            )

            yt_name = (
                loc.get("town", {})
                .get("name", town)
                .lower()
                .replace(" ", "-")
            )

            w_id = (
                loc.get("town", {})
                .get("woeid", 0)
            )

            if not w_id:
                print(
                    "[YAHOO] Passender Ort, aber keine WOEID.",
                    flush=True
                )
                continue

            if yr_name:
                url_slug = (
                    f"{yc_code}/{yr_name}/"
                    f"{yt_name}-{w_id}"
                )
            else:
                url_slug = (
                    f"{yc_code}/{yt_name}-{w_id}"
                )

            woeid = w_id
            yahoo_match_found = True

            print(
                f"[YAHOO] Match: "
                f"{yt_name}, {yc_code.upper()} "
                f"WOEID={woeid}",
                flush=True
            )

            break

        except Exception as e:
            print(
                f"[YAHOO] Versuch {attempt + 1} "
                f"fehlgeschlagen: {e}",
                flush=True
            )

            time.sleep(0.4)

    if not yahoo_match_found:
        print(
            f"[YAHOO] Kein sicherer Match fuer "
            f"{full_name!r}; "
            f"verwende keinen fremden Yahoo-Ort.",
            flush=True
        )

    return town, full_name, url_slug, woeid
