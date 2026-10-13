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
    source = get_mount_source()

    if not source:
        return "Kein USB-Gerät erkannt"

    try:
        label = run_command(
            ["lsblk", "-no", "LABEL", source]
        ).stdout.strip()
    except Exception:
        label = ""

    base = Path(source).name
    disk = get_disk_name(source)

    if label == "IPOD":
        return "iPod Classic"

    if label:
        return f"{label} ({base})"

    if disk:
        return f"{base} auf {disk}"

    return base

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
    # Auch bei einem Fehlklick ausschließlich den
    # derzeit eingebundenen iPod berücksichtigen.
    source = get_mount_source()

    expected = os.path.realpath(
        "/dev/disk/by-uuid/3845-4167"
    )

    if not source or os.path.realpath(source) != expected:
        notify(
            "Mira USB",
            "iPod nicht eindeutig erkannt",
            xbmcgui.NOTIFICATION_WARNING, 4500
        )
        return

    if get_partition_transport(source) != "usb":
        notify(
            "Mira USB",
            "Abbruch: kein USB-Massenspeicher",
            xbmcgui.NOTIFICATION_ERROR, 4500
        )
        return

    # Nur Wiedergabe von diesem Datenträger stoppen.
    playing_path = xbmc.getInfoLabel(
        "Player.FilenameAndPath"
    ).strip()

    if playing_path.startswith("/mnt/ipod/"):
        xbmc.Player().stop()
        xbmc.sleep(600)

    # Keine frei wählbaren sudo-Parameter oder Gerätepfade.
    result = run_command([
        "sudo", "-n", "/usr/bin/systemctl",
        "start", "mira-ipod-eject.service"
    ])

    if result.returncode == 0:
        notify(
            "Mira USB",
            "iPod sicher ausgehängt – jetzt abziehen",
            xbmcgui.NOTIFICATION_INFO, 5000
        )
    else:
        xbmc.log(
            "[Mira USB Eject] " +
            (result.stderr or result.stdout or "Fehlgeschlagen"),
            xbmc.LOGERROR
        )
        notify(
            "Mira USB",
            "Auswerfen fehlgeschlagen – Gerät nicht abziehen",
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
