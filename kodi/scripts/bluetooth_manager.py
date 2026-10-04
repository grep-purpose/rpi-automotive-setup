#!/usr/bin/env python3

import subprocess
import sys
import re

import xbmc
import xbmcgui


HOME = xbmcgui.Window(10000)
MAX_DEVICES = 10


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

    else:
        sync()


if __name__ == "__main__":
    main()
