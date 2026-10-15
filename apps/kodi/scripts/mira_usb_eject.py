#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

import xbmc
import xbmcgui

HOME = xbmcgui.Window(10000)
MOUNTPOINT = Path("/mnt/ipod")
DIALOG_ID = 1167

def run_command(command):
    return subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False
    )

def get_mount_source():
    result = run_command([
        "findmnt", "-rn", "-t", "vfat",
        "-o", "SOURCE", "--mountpoint", str(MOUNTPOINT)
    ])
    value = result.stdout.strip().splitlines()
    source = value[0] if len(value) == 1 else ""
    return source if source.startswith("/dev/") else ""

def get_partition_transport(source):
    parent = get_disk_name(source)
    if not parent:
        return ""
    result = run_command(
        ["lsblk", "-dnro", "TRAN", "/dev/" + parent]
    )
    return result.stdout.strip().lower()

def get_disk_name(source):
    result = run_command(
        ["lsblk", "-no", "PKNAME", source]
    )
    name = result.stdout.strip()
    return name

def get_device_label():
    import sys
    sys.path.insert(0, "/home/pi")
    from mira_usb_status import get_devices

    try:
        devices = get_devices()
        if len(devices) == 1:
            return devices[0]["name"]
        if len(devices) > 1:
            return "Mehrere USB-Geräte"
        return "Kein USB-Gerät erkannt"
    except Exception:
        return "USB-Gerät nicht eindeutig erkannt"


def notify(title, message, level=xbmcgui.NOTIFICATION_INFO, ms=3500):
    xbmcgui.Dialog().notification(title, message, level, ms)

def stop_usb_playback_if_needed():
    playing_path = xbmc.getInfoLabel("Player.FilenameAndPath").strip()

    if playing_path.startswith(str(MOUNTPOINT) + "/"):
        try:
            xbmc.Player().stop()
            xbmc.sleep(500)
        except Exception:
            pass

def open_dialog():
    HOME.setProperty("Mira.USB.EjectDeviceLabel", get_device_label())
    xbmc.executebuiltin(f"ActivateWindow({DIALOG_ID})")

def safe_eject():
    import sys
    sys.path.insert(0, "/home/pi")
    from mira_usb_status import get_devices

    try:
        devices = get_devices()

        if len(devices) != 1:
            notify(
                "Mira USB",
                "USB-Gerät nicht eindeutig erkannt",
                xbmcgui.NOTIFICATION_WARNING, 4500
            )
            return

        device = devices[0]
        mount = device["mount"]

        # Wiedergabe ausschließlich für dieses Medium stoppen.
        current = xbmc.getInfoLabel(
            "Player.FilenameAndPath"
        ).strip()

        if current.startswith(mount.rstrip("/") + "/"):
            xbmc.Player().stop()
            xbmc.sleep(600)

        result = subprocess.run(
            [
                "sudo", "-n",
                "/usr/local/sbin/mira-usb-eject-root"
            ],
            text=True,
            capture_output=True,
            timeout=60,
            check=False
        )

        if result.returncode == 0:
            HOME.setProperty(
                "Mira.USB.DeviceName",
                "Keine USB-Quelle"
            )
            notify(
                "Mira USB",
                "Sicher ausgehängt - jetzt abziehen",
                xbmcgui.NOTIFICATION_INFO, 5000
            )
        else:
            xbmc.log(
                "[Mira USB Eject] "
                + (result.stderr or result.stdout),
                xbmc.LOGERROR
            )
            notify(
                "Mira USB",
                "Auswerfen fehlgeschlagen - nicht abziehen",
                xbmcgui.NOTIFICATION_ERROR, 5000
            )

    except Exception as exc:
        xbmc.log(
            "[Mira USB Eject] " + str(exc),
            xbmc.LOGERROR
        )
        notify(
            "Mira USB",
            "Auswerfen fehlgeschlagen - nicht abziehen",
            xbmcgui.NOTIFICATION_ERROR, 5000
        )


def main():
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "open"

    if mode == "open":
        open_dialog()
    elif mode == "confirm":
        safe_eject()

if __name__ == "__main__":
    main()
