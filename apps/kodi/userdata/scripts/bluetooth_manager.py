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

    return devices[:MAX_DEVICES]



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
            {"mac": mac.upper()},
            indent=2,
        )
        + "\n"
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


def sync():
    set_power_property()
    clear_device_properties()

    devices = get_devices()

    for i, device in enumerate(devices, start=1):
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

    set_preferred_properties()


def toggle_power():
    if adapter_powered():
        run_bt("power", "off")
        notify("Bluetooth", "Bluetooth ausgeschaltet")
    else:
        run_bt("power", "on")
        notify("Bluetooth", "Bluetooth eingeschaltet")

    xbmc.sleep(600)
    sync()


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

    notify("Bluetooth", "Gerätesuche abgeschlossen")


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "sync"

    if action == "sync":
        sync()

    elif action == "toggle":
        toggle_power()

    elif action == "device" and len(sys.argv) > 2:
        try:
            device_action(int(sys.argv[2]))
        except ValueError:
            pass

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
