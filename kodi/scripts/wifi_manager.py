import json
import subprocess
import sys
from pathlib import Path

import xbmc
import xbmcgui

WINDOW = xbmcgui.Window(10000)

CACHE = Path(
    "/home/pi/.kodi/userdata/rnse_wifi_networks.json"
)

MAX_NETWORKS = 10


def log(text):
    xbmc.log(
        "RNSE WLAN: %s" % text,
        xbmc.LOGINFO
    )


def run(args, timeout=20):
    try:
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )

        return (
            result.returncode,
            result.stdout.strip(),
            result.stderr.strip()
        )

    except Exception as e:
        return 1, "", str(e)


def prop(name, value=""):
    WINDOW.setProperty(
        "RNSE.WLAN." + name,
        str(value)
    )


def clear_properties():
    for i in range(1, MAX_NETWORKS + 1):
        prop("SSID%d" % i, "")
        prop("Info%d" % i, "")
        prop("Security%d" % i, "")
        prop("Active%d" % i, "")


def scan():
    clear_properties()

    code, out, err = run([
        "nmcli",
        "--terse",
        "--escape",
        "no",
        "-f",
        "IN-USE,SSID,SIGNAL,SECURITY",
        "device",
        "wifi",
        "list",
        "ifname",
        "wlan0",
        "--rescan",
        "yes",
    ])

    if code != 0:
        log("Scan fehlgeschlagen: %s" % err)

        xbmcgui.Dialog().notification(
            "WLAN",
            "Netzwerksuche fehlgeschlagen",
            xbmcgui.NOTIFICATION_ERROR,
            2500
        )

        return

    # SSID -> stärkster Eintrag
    networks = {}

    for raw in out.splitlines():
        if not raw.strip():
            continue

        # nmcli liefert:
        # IN-USE:SSID:SIGNAL:SECURITY
        parts = raw.split(":", 3)

        if len(parts) != 4:
            continue

        in_use, ssid, signal, security = parts

        ssid = ssid.strip()

        # versteckte/leere SSIDs nicht anzeigen
        if not ssid:
            continue

        try:
            signal_int = int(signal)
        except Exception:
            signal_int = 0

        entry = {
            "ssid": ssid,
            "signal": signal_int,
            "security": security.strip(),
            "active": in_use.strip() == "*"
        }

        old = networks.get(ssid)

        if (
            old is None
            or entry["active"]
            or entry["signal"] > old["signal"]
        ):
            networks[ssid] = entry

    # Verbundenes Netz zuerst, danach Signalstärke
    result = sorted(
        networks.values(),
        key=lambda x: (
            not x["active"],
            -x["signal"],
            x["ssid"].lower()
        )
    )

    result = result[:MAX_NETWORKS]

    CACHE.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    for i, network in enumerate(result, 1):
        prop(
            "SSID%d" % i,
            network["ssid"]
        )

        if network["active"]:
            info = "verbunden · %d %%" % network["signal"]
        else:
            info = "%d %%" % network["signal"]

        prop(
            "Info%d" % i,
            info
        )

        prop(
            "Security%d" % i,
            network["security"]
        )

        prop(
            "Active%d" % i,
            "1" if network["active"] else "0"
        )

    log(
        "%d Netzwerke gefunden"
        % len(result)
    )


def load_cache():
    try:
        return json.loads(
            CACHE.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return []


def ask_password(ssid):
    keyboard = xbmc.Keyboard(
        "",
        "Passwort für %s" % ssid,
        True
    )

    keyboard.doModal()

    if not keyboard.isConfirmed():
        return None

    return keyboard.getText()


def refresh_after_connect():
    xbmc.sleep(1000)
    scan()


def connect(slot):
    networks = load_cache()

    index = slot - 1

    if index < 0 or index >= len(networks):
        xbmcgui.Dialog().notification(
            "WLAN",
            "Netzwerk nicht mehr verfügbar",
            xbmcgui.NOTIFICATION_ERROR,
            2500
        )

        scan()
        return

    network = networks[index]

    ssid = network["ssid"]
    security = network.get("security", "")
    active = network.get("active", False)

    if active:
        xbmcgui.Dialog().notification(
            "WLAN",
            "%s ist bereits verbunden" % ssid,
            xbmcgui.NOTIFICATION_INFO,
            1800
        )
        return

    xbmcgui.Dialog().notification(
        "WLAN",
        "Verbinde mit %s ..." % ssid,
        xbmcgui.NOTIFICATION_INFO,
        1500
    )

    # --------------------------------------------------------
    # Zuerst ohne Passwort versuchen.
    # Funktioniert bei bereits gespeicherten Verbindungen.
    # --------------------------------------------------------

    code, out, err = run([
        "nmcli",
        "device",
        "wifi",
        "connect",
        ssid,
        "ifname",
        "wlan0"
    ])

    if code == 0:
        xbmcgui.Dialog().notification(
            "WLAN",
            "Mit %s verbunden" % ssid,
            xbmcgui.NOTIFICATION_INFO,
            2500
        )

        refresh_after_connect()
        return

    log(
        "Verbindung ohne Passwort fehlgeschlagen: %s"
        % err
    )

    # --------------------------------------------------------
    # Offenes Netz?
    # Dann gibt es nichts weiter zu fragen.
    # --------------------------------------------------------

    security_upper = security.upper()

    if (
        not security_upper
        or security_upper == "--"
        or security_upper == "NONE"
    ):
        xbmcgui.Dialog().notification(
            "WLAN",
            "Verbindung fehlgeschlagen",
            xbmcgui.NOTIFICATION_ERROR,
            2500
        )

        return

    # --------------------------------------------------------
    # Neues geschütztes Netz:
    # Kodi-Bildschirmtastatur öffnen
    # --------------------------------------------------------

    password = ask_password(ssid)

    if password is None:
        return

    if not password:
        xbmcgui.Dialog().notification(
            "WLAN",
            "Kein Passwort eingegeben",
            xbmcgui.NOTIFICATION_WARNING,
            2000
        )

        return

    code, out, err = run([
        "nmcli",
        "device",
        "wifi",
        "connect",
        ssid,
        "password",
        password,
        "ifname",
        "wlan0"
    ])

    # Passwort danach nicht weiter behalten
    password = None

    if code == 0:
        xbmcgui.Dialog().notification(
            "WLAN",
            "Mit %s verbunden" % ssid,
            xbmcgui.NOTIFICATION_INFO,
            2500
        )

        refresh_after_connect()

    else:
        log(
            "Verbindung fehlgeschlagen: %s"
            % err
        )

        xbmcgui.Dialog().notification(
            "WLAN",
            "Verbindung mit %s fehlgeschlagen" % ssid,
            xbmcgui.NOTIFICATION_ERROR,
            3000
        )


mode = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "scan"
)

if mode == "scan":
    scan()

elif mode == "connect":
    try:
        slot = int(sys.argv[2])
    except Exception:
        slot = 0

    connect(slot)
