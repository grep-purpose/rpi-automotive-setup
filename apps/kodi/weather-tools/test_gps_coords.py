import socket
import subprocess
import re

mac = "F4:2B:8C:23:CD:78"
print(f"Suche SPP-Kanal fuer {mac}...")

try:
    sdp = subprocess.check_output(f"sdptool search --bdaddr {mac} SP", shell=True, timeout=8).decode()
    match = re.search(r"Channel:\s+(\d+)", sdp)
    if not match:
        print("Kein SPP-Kanal in SDP gefunden!")
        exit(1)
    channel = int(match.group(1))
    print(f"SPP-Kanal gefunden: {channel}")

    print("Verbinde Bluetooth-Socket...")
    s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    s.settimeout(5.0)
    s.connect((mac, channel))
    print("Verbunden! Lese NMEA-Daten...")

    buffer = ""
    for i in range(15):
        chunk = s.recv(1024).decode("ascii", errors="replace")
        buffer += chunk
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if line.startswith(("$GNGGA", "$GPGGA", "$GNRMC", "$GPRMC")):
                print(f"Empfangen: {line}")
                parts = line.split(",")
                # Pruefen auf GGA Fix
                if "GGA" in parts[0] and len(parts) > 5 and parts[2] and parts[4]:
                    raw_lat, lat_dir = float(parts[2]), parts[3]
                    raw_lon, lon_dir = float(parts[4]), parts[5]
                    lat = (int(raw_lat / 100)) + (raw_lat % 100) / 60.0
                    if lat_dir == 'S': lat = -lat
                    lon = (int(raw_lon / 100)) + (raw_lon % 100) / 60.0
                    if lon_dir == 'W': lon = -lon
                    print(f"--> ERFOLG! Koordinaten: {round(lat, 5)}, {round(lon, 5)}")
                    s.close()
                    exit(0)
    s.close()
    print("Kein vollstaendiger GGA-Satz mit Fix empfangen.")
except Exception as e:
    print(f"Fehler aufgetreten: {e}")
