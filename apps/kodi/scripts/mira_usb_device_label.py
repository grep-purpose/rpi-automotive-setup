#!/usr/bin/env python3
"""Mira USB: Gerätename aus dem zentralen Gerätestatus."""

import sys

import xbmc
import xbmcgui

sys.path.insert(0, "/home/pi")

from mira_usb_status import get_devices


def main():
    home = xbmcgui.Window(10000)

    try:
        devices = get_devices()

        if len(devices) == 1:
            name = devices[0]["name"]
        elif len(devices) > 1:
            name = "Mehrere USB-Geräte"
        else:
            name = "Keine USB-Quelle"

    except Exception as exc:
        xbmc.log(
            "[Mira USB] Geräteerkennung fehlgeschlagen: "
            + str(exc),
            xbmc.LOGERROR
        )
        name = "USB-Speicher"

    home.setProperty("Mira.USB.DeviceName", name)

    xbmc.log(
        "[Mira USB] Aktiver Gerätename: " + name,
        xbmc.LOGINFO
    )


if __name__ == "__main__":
    main()
