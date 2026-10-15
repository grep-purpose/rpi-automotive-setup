#!/usr/bin/env python3
"""Mira USB: Kodi-Gerätename automatisch synchronisieren."""

import sys
import xbmc
import xbmcgui

sys.path.insert(0, "/home/pi")

from mira_usb_status import get_devices

PROPERTY = "Mira.USB.DeviceName"


def device_name():
    devices = get_devices()

    if len(devices) == 1:
        return devices[0]["name"]

    if len(devices) > 1:
        return "Mehrere USB-Geräte"

    return "Keine USB-Quelle"


def main():
    monitor = xbmc.Monitor()
    home = xbmcgui.Window(10000)
    previous = None

    xbmc.log("[Mira USB Monitor] Gestartet", xbmc.LOGINFO)

    while not monitor.abortRequested():
        try:
            current = device_name()

            # Auch Änderungen durch andere Skripte erkennen.
            displayed = home.getProperty(PROPERTY)

            if current != previous or displayed != current:
                home.setProperty(PROPERTY, current)
                previous = current

                xbmc.log(
                    "[Mira USB Monitor] Gerätename: " + current,
                    xbmc.LOGINFO
                )

        except Exception as exc:
            xbmc.log(
                "[Mira USB Monitor] " + str(exc),
                xbmc.LOGWARNING
            )

        if monitor.waitForAbort(3):
            break


if __name__ == "__main__":
    main()
