#!/usr/bin/env python3

import subprocess
import sys
import re
import json
from pathlib import Path

import xbmc
import xbmcgui


HOME = xbmcgui.Window(10000)
MAX_DEVICES = 10

PREFERRED_FILE = Path.home() / ".kodi/userdata/rnse_bluetooth_preferred.json"
AUTOSTART_FILE = Path.home() / ".config/rnse-bluetooth/autoconnect_devices"

PHONE_AUDIO_UUIDS = (
    "0000110a",  # Audio Source
    "0000110d",  # Advanced Audio Distribution
    "0000111f",  # Handsfree Audio Gateway
    "00001112",  # Headset AG
)


def run_bt(*args, timeout=15):
    try:
        result = subprocess.run(
            ["bluetoothctl", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as exc:
        return 1, "", str(exc)


def notify(title, message, ms=2500):
    xbmc.executebuiltin(
        f'Notification("{title}","{message}",{ms})'
    )


def parse_bool(text, field):
    match = re.search(
        rf"^\s*{re.escape(field)}:\s*(yes|no)\s*$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    return bool(match and match.group(1).lower() == "yes")


def adapter_powered():
    _, out, _ = run_bt("show")
    return parse_bool(out, "Powered")


def set_power_property():
    HOME.setProperty(
        "RNSE.Bluetooth.EnabledState",
        "on" if adapter_powered() else "off",
    )


def get_devices():
    _, out, _ = run_bt("devices")

    devices = []

    for line in out.splitlines():
        match = re.match(
            r"^Device\s+([0-9A-Fa-f:]{17})\s+(.+)$",
            line.strip(),
        )

        if not match:
            continue

        mac = match.group(1).upper()
        fallback_name = match.group(2).strip()

        _, info, _ = run_bt("info", mac)

        name_match = re.search(
            r"^\s*(?:Alias|Name):\s*(.+)$",
            info,
            re.MULTILINE,
        )

        name = (
            name_match.group(1).strip()
            if name_match
            else fallback_name
        )

        paired = parse_bool(info, "Paired")
        connected = parse_bool(info, "Connected")
        trusted = parse_bool(info, "Trusted")

        if connected:
            status = "Verbunden"
        elif paired:
            status = "Gekoppelt"
        else:
            status = "Verfügbar"

        devices.append(
            {
                "mac": mac,
                "name": name,
                "paired": paired,
                "connected": connected,
                "trusted": trusted,
                "status": status,
                "info": info,
            }
        )

    # Verbundene zuerst, danach gekoppelte, dann Rest.
    devices.sort(
        key=lambda d: (
            not d["connected"],
            not d["paired"],
            d["name"].lower(),
        )
    )

    return devices



def is_phone_audio_device(device):
    info = device.get("info", "")
    return device.get("paired", False) and any(
        uuid in info.lower()
        for uuid in PHONE_AUDIO_UUIDS
    )


def load_preferred_mac():
    try:
        data = json.loads(PREFERRED_FILE.read_text())
        mac = str(data.get("mac", "")).upper().strip()

        if re.fullmatch(r"[0-9A-F]{2}(?::[0-9A-F]{2}){5}", mac):
            return mac
    except Exception:
        pass

    return ""


def save_preferred_mac(mac):
    PREFERRED_FILE.parent.mkdir(parents=True, exist_ok=True)

    PREFERRED_FILE.write_text(
        json.dumps(
            {"mac": mac.upper() if mac else ""},
            indent=2,
        )
        + "\n"
    )



def load_autostart_macs():
    try:
        lines = AUTOSTART_FILE.read_text().splitlines()

        result = set()

        for line in lines:
            mac = line.strip().upper()

            if re.fullmatch(
                r"[0-9A-F]{2}(?::[0-9A-F]{2}){5}",
                mac,
            ):
                result.add(mac)

        return result

    except Exception:
        # Solange noch keine eigene Config existiert,
        # behandeln wir das bevorzugte Telefon als erlaubt.
        preferred = load_preferred_mac()

        return {preferred} if preferred else set()


def save_autostart_macs(macs):
    AUTOSTART_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    content = "\n".join(sorted(macs))

    if content:
        content += "\n"

    AUTOSTART_FILE.write_text(content)


def set_autostart_allowed(mac, allowed):
    mac = mac.upper()
    macs = load_autostart_macs()

    if allowed:
        macs.add(mac)
    else:
        macs.discard(mac)

    save_autostart_macs(macs)


def device_by_mac(mac):
    mac = mac.upper()

    for device in get_devices():
        if device["mac"] == mac:
            return device

    return None


def set_detail_properties(mac=None):
    if not mac:
        mac = HOME.getProperty(
            "RNSE.Bluetooth.Detail.MAC"
        )

    if not mac:
        return

    device = device_by_mac(mac)

    if not device:
        return

    autostart = (
        device["mac"] in load_autostart_macs()
    )

    HOME.setProperty(
        "RNSE.Bluetooth.Detail.MAC",
        device["mac"],
    )

    HOME.setProperty(
        "RNSE.Bluetooth.Detail.Name",
        device["name"],
    )

    HOME.setProperty(
        "RNSE.Bluetooth.Detail.Status",
        device["status"],
    )

    HOME.setProperty(
        "RNSE.Bluetooth.Detail.Connected",
        "true" if device["connected"] else "false",
    )

    HOME.setProperty(
        "RNSE.Bluetooth.Detail.Autostart",
        "true" if autostart else "false",
    )

    HOME.setProperty(
        "RNSE.Bluetooth.Detail.ConnectionAction",
        "Trennen"
        if device["connected"]
        else "Verbinden",
    )



def get_preferred_candidates():
    return [
        device
        for device in get_devices()
        if is_phone_audio_device(device)
    ]


def set_preferred_properties():
    preferred_mac = load_preferred_mac()
    candidates = get_preferred_candidates()

    preferred_name = "Nicht festgelegt"

    for device in candidates:
        if device["mac"] == preferred_mac:
            preferred_name = device["name"]
            break

    HOME.setProperty(
        "RNSE.Bluetooth.Preferred.Name",
        preferred_name,
    )

    HOME.setProperty(
        "RNSE.Bluetooth.Preferred.MAC",
        preferred_mac,
    )

    for i in range(1, MAX_DEVICES + 1):
        for field in ("Name", "MAC", "Selected"):
            HOME.clearProperty(
                f"RNSE.Bluetooth.Preferred{i}.{field}"
            )

    for i, device in enumerate(candidates[:MAX_DEVICES], start=1):
        base = f"RNSE.Bluetooth.Preferred{i}"

        HOME.setProperty(
            f"{base}.Name",
            device["name"],
        )

        HOME.setProperty(
            f"{base}.MAC",
            device["mac"],
        )

        HOME.setProperty(
            f"{base}.Selected",
            "true" if device["mac"] == preferred_mac else "false",
        )


def preferred_action(index):
    candidates = get_preferred_candidates()

    if index < 1 or index > len(candidates):
        return

    device = candidates[index - 1]

    save_preferred_mac(device["mac"])

    notify(
        "Bluetooth",
        f"{device['name']} ist jetzt bevorzugtes Telefon",
        2500,
    )

    sync()


def clear_device_properties():
    # DeviceX wird auf der Hauptseite ausschließlich für
    # aktuell gefundene, noch nicht gekoppelte Geräte verwendet.
    for i in range(1, MAX_DEVICES + 1):
        for field in (
            "Name",
            "MAC",
            "Status",
            "Paired",
            "Connected",
            "Trusted",
        ):
            HOME.clearProperty(
                f"RNSE.Bluetooth.Device{i}.{field}"
            )


def clear_paired_properties():
    HOME.clearProperty("RNSE.Bluetooth.Paired.Count")
    HOME.clearProperty("RNSE.Bluetooth.Paired.CountLabel")

    for i in range(1, MAX_DEVICES + 1):
        for field in (
            "Name",
            "MAC",
            "Status",
            "Paired",
            "Connected",
            "Trusted",
        ):
            HOME.clearProperty(
                f"RNSE.Bluetooth.Paired{i}.{field}"
            )


def get_paired_devices():
    devices = [
        device
        for device in get_devices()
        if device["paired"]
    ]

    devices.sort(
        key=lambda d: (
            not d["connected"],
            d["name"].lower(),
        )
    )

    return devices


def get_discovered_devices():
    # Auf der Hauptseite sollen nach einer Suche nur Geräte
    # erscheinen, die noch NICHT gekoppelt sind.
    devices = [
        device
        for device in get_devices()
        if not device["paired"]
    ]

    devices.sort(
        key=lambda d: d["name"].lower()
    )

    return devices


def set_paired_properties():
    clear_paired_properties()

    devices = get_paired_devices()
    count = len(devices)

    HOME.setProperty(
        "RNSE.Bluetooth.Paired.Count",
        str(count),
    )

    HOME.setProperty(
        "RNSE.Bluetooth.Paired.CountLabel",
        f"{count} Gerät" if count == 1 else f"{count} Geräte",
    )

    for i, device in enumerate(
        devices[:MAX_DEVICES],
        start=1,
    ):
        base = f"RNSE.Bluetooth.Paired{i}"

        HOME.setProperty(f"{base}.Name", device["name"])
        HOME.setProperty(f"{base}.MAC", device["mac"])
        HOME.setProperty(f"{base}.Status", device["status"])

        HOME.setProperty(
            f"{base}.Paired",
            "true" if device["paired"] else "false",
        )

        HOME.setProperty(
            f"{base}.Connected",
            "true" if device["connected"] else "false",
        )

        HOME.setProperty(
            f"{base}.Trusted",
            "true" if device["trusted"] else "false",
        )


def set_discovered_properties():
    clear_device_properties()

    devices = get_discovered_devices()

    for i, device in enumerate(
        devices[:MAX_DEVICES],
        start=1,
    ):
        base = f"RNSE.Bluetooth.Device{i}"

        HOME.setProperty(f"{base}.Name", device["name"])
        HOME.setProperty(f"{base}.MAC", device["mac"])
        HOME.setProperty(f"{base}.Status", device["status"])

        HOME.setProperty(
            f"{base}.Paired",
            "true" if device["paired"] else "false",
        )

        HOME.setProperty(
            f"{base}.Connected",
            "true" if device["connected"] else "false",
        )

        HOME.setProperty(
            f"{base}.Trusted",
            "true" if device["trusted"] else "false",
        )


def sync():
    set_power_property()
    set_paired_properties()
    set_preferred_properties()


def main_sync():
    # Beim neuen Öffnen der Bluetooth-Hauptseite keine alten
    # Scan-Ergebnisse vom vorherigen Besuch anzeigen.
    clear_device_properties()
    sync()


def toggle_power():
    if adapter_powered():
        run_bt("power", "off")
        notify("Bluetooth", "Bluetooth ausgeschaltet")
    else:
        run_bt("power", "on")
        notify("Bluetooth", "Bluetooth eingeschaltet")

    xbmc.sleep(600)
    main_sync()


def device_action(index):
    sync()

    base = f"RNSE.Bluetooth.Device{index}"

    mac = HOME.getProperty(f"{base}.MAC")
    name = HOME.getProperty(f"{base}.Name")
    paired = HOME.getProperty(f"{base}.Paired") == "true"
    connected = HOME.getProperty(f"{base}.Connected") == "true"

    if not mac:
        return

    if connected:
        notify("Bluetooth", f"{name} wird getrennt …")
        code, _, err = run_bt("disconnect", mac, timeout=20)

        if code != 0:
            notify(
                "Bluetooth",
                f"Trennen fehlgeschlagen: {err or name}",
                3500,
            )

    elif paired:
        # Bereits gekoppelte Geräte beim Verbindungsversuch
        # automatisch als vertrauenswürdig markieren.
        run_bt("trust", mac, timeout=5)

        notify("Bluetooth", f"{name} wird verbunden …")

        code, out, err = run_bt("connect", mac, timeout=8)

        if code != 0:
            message = err or out or "Gerät nicht erreichbar"

            # bluetoothctl-Ausgaben können sehr lang sein.
            message = message.replace("\n", " ").strip()

            if len(message) > 90:
                message = message[:87] + "..."

            notify(
                "Bluetooth",
                f"Verbindung fehlgeschlagen: {message}",
                3500,
            )

    else:
        notify(
            "Bluetooth",
            "Pairing neuer Geräte folgt im nächsten Schritt",
            3000,
        )

    xbmc.sleep(1000)
    sync()



def paired_action(index):
    sync()

    base = f"RNSE.Bluetooth.Paired{index}"

    mac = HOME.getProperty(f"{base}.MAC")

    if not mac:
        return

    set_detail_properties(mac)

    xbmc.executebuiltin(
        "ActivateWindow(1163)"
    )


def detail_refresh():
    set_detail_properties()


def detail_toggle_autostart():
    mac = HOME.getProperty(
        "RNSE.Bluetooth.Detail.MAC"
    )

    if not mac:
        return

    current = (
        HOME.getProperty(
            "RNSE.Bluetooth.Detail.Autostart"
        )
        == "true"
    )

    set_autostart_allowed(
        mac,
        not current,
    )

    set_detail_properties(mac)


def detail_connection():
    mac = HOME.getProperty(
        "RNSE.Bluetooth.Detail.MAC"
    )

    name = HOME.getProperty(
        "RNSE.Bluetooth.Detail.Name"
    )

    if not mac:
        return

    device = device_by_mac(mac)

    if not device:
        return

    if device["connected"]:
        notify(
            "Bluetooth",
            f"{name} wird getrennt …",
        )

        code, _, err = run_bt(
            "disconnect",
            mac,
            timeout=20,
        )

        if code != 0:
            notify(
                "Bluetooth",
                f"Trennen fehlgeschlagen: {err or name}",
                3500,
            )

    else:
        run_bt(
            "trust",
            mac,
            timeout=5,
        )

        notify(
            "Bluetooth",
            f"{name} wird verbunden …",
        )

        code, out, err = run_bt(
            "connect",
            mac,
            timeout=8,
        )

        if code != 0:
            message = (
                err
                or out
                or "Gerät nicht erreichbar"
            )

            message = (
                message
                .replace("\n", " ")
                .strip()
            )

            if len(message) > 90:
                message = message[:87] + "..."

            notify(
                "Bluetooth",
                f"Verbindung fehlgeschlagen: {message}",
                3500,
            )

    xbmc.sleep(1000)

    sync()
    set_detail_properties(mac)


def detail_forget():
    mac = HOME.getProperty(
        "RNSE.Bluetooth.Detail.MAC"
    )

    name = HOME.getProperty(
        "RNSE.Bluetooth.Detail.Name"
    )

    if not mac:
        return

    # Gerät auch aus Autostart-Berechtigung entfernen.
    set_autostart_allowed(
        mac,
        False,
    )

    code, out, err = run_bt(
        "remove",
        mac,
        timeout=15,
    )

    if code != 0:
        message = (
            err
            or out
            or "Gerät konnte nicht entfernt werden"
        )

        notify(
            "Bluetooth",
            message.replace("\n", " ")[:90],
            3500,
        )

        return

    # Falls das gelöschte Gerät bevorzugtes Telefon war,
    # Auswahl ebenfalls zurücksetzen.
    if load_preferred_mac() == mac:
        save_preferred_mac("")

    notify(
        "Bluetooth",
        f"{name} wurde entfernt",
        2500,
    )

    sync()

    xbmc.executebuiltin(
        "Action(Back)"
    )



def scan():
    if not adapter_powered():
        run_bt("power", "on", timeout=5)
        xbmc.sleep(500)

    # In unserem Automotive-System hat eine bestehende
    # Bluetooth-Audioverbindung Vorrang vor Discovery.
    #
    # Der Raspberry-Pi-Bluetooth-Stack hat beim bisherigen
    # parallelen Scan die aktive A2DP-Verbindung beschädigt.
    for device in get_devices():
        if device["connected"]:
            notify(
                "Bluetooth",
                "Gerätesuche während aktiver Bluetooth-Verbindung nicht verfügbar",
                3500,
            )
            return

    notify("Bluetooth", "Suche nach Geräten gestartet")

    try:
        process = subprocess.Popen(
            ["bluetoothctl", "scan", "on"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Kodi bleibt währenddessen kontrollierbar.
        monitor = xbmc.Monitor()

        for _ in range(12):
            if monitor.abortRequested():
                break
            xbmc.sleep(500)

    except Exception as exc:
        notify(
            "Bluetooth",
            "Gerätesuche konnte nicht gestartet werden",
            3000,
        )

    finally:
        run_bt("scan", "off", timeout=5)

        try:
            if "process" in locals() and process.poll() is None:
                process.terminate()
        except Exception:
            pass

    xbmc.sleep(500)
    sync()
    set_discovered_properties()

    notify("Bluetooth", "Gerätesuche abgeschlossen")


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "sync"

    if action == "sync":
        sync()

    elif action == "main_sync":
        main_sync()

    elif action == "toggle":
        toggle_power()

    elif action == "device" and len(sys.argv) > 2:
        try:
            device_action(int(sys.argv[2]))
        except ValueError:
            pass

    elif action == "paired" and len(sys.argv) > 2:
        try:
            paired_action(int(sys.argv[2]))
        except ValueError:
            pass

    elif action == "detail_refresh":
        detail_refresh()

    elif action == "detail_autostart":
        detail_toggle_autostart()

    elif action == "detail_connection":
        detail_connection()

    elif action == "detail_forget":
        detail_forget()

    elif action == "scan":
        scan()

    elif action == "preferred" and len(sys.argv) > 2:
        try:
            preferred_action(int(sys.argv[2]))
        except ValueError:
            pass

    else:
        sync()


if __name__ == "__main__":
    main()
