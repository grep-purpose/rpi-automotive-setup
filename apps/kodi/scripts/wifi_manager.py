import json
import subprocess
import sys
from pathlib import Path

import xbmc
import xbmcgui


WINDOW = xbmcgui.Window(10000)

NETWORK_CACHE = Path(
    "/home/pi/.kodi/userdata/rnse_wifi_networks.json"
)

SAVED_CACHE = Path(
    "/home/pi/.kodi/userdata/rnse_wifi_saved.json"
)

MAX_NETWORKS = 10
MAX_SAVED = 15


def log(text):
    xbmc.log(
        "RNSE WLAN: %s" % text,
        xbmc.LOGINFO
    )


def run(args, timeout=60):
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

    except subprocess.TimeoutExpired:
        return 124, "", "Zeitüberschreitung"

    except Exception as e:
        return 1, "", str(e)


def prop(name, value=""):
    WINDOW.setProperty(
        "RNSE.WLAN." + name,
        str(value)
    )


# ============================================================
# WLAN EIN / AUS
# ============================================================

def wifi_enabled():
    code, out, err = run([
        "nmcli",
        "radio",
        "wifi"
    ])

    return (
        code == 0
        and out.strip().lower() == "enabled"
    )


def sync_wifi_state():
    if wifi_enabled():
        prop("EnabledState", "on")
        return True

    prop("EnabledState", "off")
    return False


def toggle_wifi():
    if wifi_enabled():

        code, out, err = run([
            "nmcli",
            "radio",
            "wifi",
            "off"
        ])

        if code == 0:
            prop("EnabledState", "off")
            clear_network_properties()

            xbmcgui.Dialog().notification(
                "WLAN",
                "WLAN ausgeschaltet",
                xbmcgui.NOTIFICATION_INFO,
                1800
            )

            xbmc.sleep(300)
            xbmc.executebuiltin("SetFocus(9300)")
            xbmc.executebuiltin("Action(FirstPage)")

        else:
            xbmcgui.Dialog().notification(
                "WLAN",
                "WLAN konnte nicht ausgeschaltet werden",
                xbmcgui.NOTIFICATION_ERROR,
                2500
            )

    else:

        code, out, err = run([
            "nmcli",
            "radio",
            "wifi",
            "on"
        ])

        if code == 0:
            prop("EnabledState", "on")

            xbmcgui.Dialog().notification(
                "WLAN",
                "WLAN eingeschaltet",
                xbmcgui.NOTIFICATION_INFO,
                1500
            )

            # Funkchip kurz hochkommen lassen
            xbmc.sleep(1200)

            scan()

        else:
            xbmcgui.Dialog().notification(
                "WLAN",
                "WLAN konnte nicht eingeschaltet werden",
                xbmcgui.NOTIFICATION_ERROR,
                2500
            )


# ============================================================
# WLAN-SCAN
# ============================================================

def clear_network_properties():
    for i in range(1, MAX_NETWORKS + 1):
        prop("SSID%d" % i, "")
        prop("Info%d" % i, "")
        prop("Security%d" % i, "")
        prop("Active%d" % i, "")


def focus_first_network():
    # Liste selbst fokussieren
    xbmc.executebuiltin("SetFocus(9300)")

    xbmc.sleep(100)

    # Wirklich ganz nach oben
    xbmc.executebuiltin("Action(FirstPage)")

    xbmc.sleep(100)

    # Zeile 1 = WLAN-Schalter
    # Eine Position runter = erstes WLAN-Netzwerk
    xbmc.executebuiltin("Action(Down)")


def scan():
    clear_network_properties()

    if not sync_wifi_state():
        log("Scan übersprungen: WLAN ist ausgeschaltet")
        return

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

    networks = {}

    for raw in out.splitlines():

        if not raw.strip():
            continue

        parts = raw.split(":", 3)

        if len(parts) != 4:
            continue

        in_use, ssid, signal, security = parts

        ssid = ssid.strip()

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

    result = sorted(
        networks.values(),
        key=lambda x: (
            not x["active"],
            -x["signal"],
            x["ssid"].lower()
        )
    )

    result = result[:MAX_NETWORKS]

    NETWORK_CACHE.write_text(
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

    # Dein funktionierender FirstPage-Fix:
    # nach jedem Scan zum ERSTEN Netzwerk.
    if result:
        xbmc.sleep(200)
        focus_first_network()


def load_network_cache():
    try:
        return json.loads(
            NETWORK_CACHE.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return []


# ============================================================
# PASSWORT
# ============================================================

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


# ============================================================
# VERBINDEN
# ============================================================

def refresh_after_connect():
    xbmc.sleep(1000)
    scan()


def connect(slot):

    networks = load_network_cache()

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
    # Erst versuchen, ein bereits gespeichertes Profil zu
    # verwenden.
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
            2200
        )

        refresh_after_connect()
        return

    log(
        "Verbindung ohne Passwort fehlgeschlagen: %s"
        % err
    )

    security_upper = security.upper()

    # Offenes Netz
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

    # Geschütztes neues Netz
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

        message = "Verbindung fehlgeschlagen"

        if "timeout" in err.lower():
            message = "Zeitüberschreitung bei Verbindung"

        elif "secret" in err.lower():
            message = "Authentifizierung fehlgeschlagen"

        xbmcgui.Dialog().notification(
            "WLAN",
            message,
            xbmcgui.NOTIFICATION_ERROR,
            3000
        )


# ============================================================
# GESPEICHERTE WLAN-NETZE
# ============================================================

def clear_saved_properties():

    for i in range(1, MAX_SAVED + 1):

        prop(
            "SavedName%d" % i,
            ""
        )

        prop(
            "SavedInfo%d" % i,
            ""
        )


def saved_networks():

    clear_saved_properties()

    code, out, err = run([
        "nmcli",
        "-t",
        "-f",
        "NAME,UUID,TYPE",
        "connection",
        "show"
    ])

    if code != 0:

        log(
            "Gespeicherte Netzwerke konnten nicht gelesen werden: %s"
            % err
        )

        return

    result = []

    for line in out.splitlines():

        if not line.strip():
            continue

        parts = line.split(":")

        if len(parts) < 3:
            continue

        name = parts[0]
        uuid = parts[1]
        conn_type = parts[2]

        if conn_type != "802-11-wireless" and conn_type != "wifi":
            continue

        # AP-/Hotspot-Profile nicht als normales WLAN anzeigen
        mode_code, mode_out, mode_err = run([
            "nmcli",
            "-g",
            "802-11-wireless.mode",
            "connection",
            "show",
            "uuid",
            uuid
        ])

        mode = mode_out.strip().lower()

        if mode in ("ap", "adhoc"):
            continue

        ssid_code, ssid_out, ssid_err = run([
            "nmcli",
            "-g",
            "802-11-wireless.ssid",
            "connection",
            "show",
            "uuid",
            uuid
        ])

        ssid = ssid_out.strip() or name

        result.append({
            "name": name,
            "ssid": ssid,
            "uuid": uuid
        })

    # Doppelte Profile mit gleicher SSID nicht mehrfach anzeigen
    unique = {}

    for entry in result:
        unique[entry["uuid"]] = entry

    result = sorted(
        unique.values(),
        key=lambda x: x["ssid"].lower()
    )

    result = result[:MAX_SAVED]

    SAVED_CACHE.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    for i, entry in enumerate(result, 1):

        prop(
            "SavedName%d" % i,
            entry["ssid"]
        )

        prop(
            "SavedInfo%d" % i,
            "gespeichert"
        )

    xbmc.sleep(150)

    xbmc.executebuiltin(
        "SetFocus(9500)"
    )

    xbmc.sleep(100)

    xbmc.executebuiltin(
        "Action(FirstPage)"
    )


def load_saved_cache():

    try:
        return json.loads(
            SAVED_CACHE.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return []


def forget(slot):

    networks = load_saved_cache()

    index = slot - 1

    if (
        index < 0
        or index >= len(networks)
    ):
        saved_networks()
        return

    network = networks[index]

    ssid = network["ssid"]
    uuid = network["uuid"]

    confirmed = xbmcgui.Dialog().yesno(
        "WLAN",
        "Netzwerk '%s' wirklich vergessen?"
        % ssid
    )

    if not confirmed:
        return

    code, out, err = run([
        "nmcli",
        "connection",
        "delete",
        "uuid",
        uuid
    ])

    if code == 0:

        xbmcgui.Dialog().notification(
            "WLAN",
            "%s wurde vergessen" % ssid,
            xbmcgui.NOTIFICATION_INFO,
            2200
        )

        xbmc.sleep(400)

        saved_networks()

    else:

        log(
            "Vergessen fehlgeschlagen: %s"
            % err
        )

        xbmcgui.Dialog().notification(
            "WLAN",
            "Netzwerk konnte nicht vergessen werden",
            xbmcgui.NOTIFICATION_ERROR,
            2500
        )


# ============================================================
# START
# ============================================================

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


elif mode == "toggle_wifi":

    toggle_wifi()


elif mode == "sync_wifi":

    sync_wifi_state()


elif mode == "saved":

    saved_networks()


elif mode == "forget":

    try:
        slot = int(sys.argv[2])
    except Exception:
        slot = 0

    forget(slot)
