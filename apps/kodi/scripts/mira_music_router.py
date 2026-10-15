#!/usr/bin/env python3

import sys
from pathlib import Path
from urllib.parse import unquote

import xbmc
import xbmcgui

USB_ROOTS = (
    Path("/mnt/ipod"),
    Path("/mnt/mira-nano-test"),
    Path("/media/pi"),
    Path("/run/media/pi"),
)

BT_WINDOW = 11199
USB_WINDOW = 1170
SOURCE_WINDOW = 1165
RADIO_WINDOW = 11198

HOME = xbmcgui.Window(10000)


def kodi_usb_playing():
    """USB-Musik anhand des aktuell verbundenen Geräts erkennen."""

    try:
        import sys
        sys.path.insert(0, "/home/pi")
        from mira_usb_status import get_devices

        if not (
            xbmc.getCondVisibility("Player.HasAudio")
            and xbmc.getCondVisibility("Player.Playing")
            and not xbmc.getCondVisibility("Player.Paused")
        ):
            return False

        filename = unquote(
            xbmc.getInfoLabel("Player.FilenameAndPath")
        ).strip()

        if not filename.startswith("/"):
            return False

        # Nur physisch vorhandene und korrekt
        # schreibgeschützt eingebundene USB-Geräte.
        devices = get_devices()

        if len(devices) != 1:
            return False

        device = devices[0]
        mount = Path(device["mount"]).resolve()
        current = Path(filename).resolve()

        return (
            current.is_relative_to(mount)
            and current != mount
        )

    except Exception as exc:
        xbmc.log(
            "[Mira USB Router] Erkennung fehlgeschlagen: "
            + str(exc),
            xbmc.LOGWARNING
        )
        return False


def bluetooth_playing():
    """Bluetooth-Status des bestehenden Mira-Monitors."""

    return (
        HOME.getProperty("RNSE.Music.Status")
        .strip()
        .lower() == "playing"
    )


# MIRA_HYBRID_ROUTING_R3

LAST_SOURCE_PROPERTY = "Mira.Music.LastSource"


def usb_connected():
    """Ein eindeutig erkanntes USB-Musikgerät ist verbunden."""
    try:
        sys.path.insert(0, "/home/pi")
        from mira_usb_status import get_devices

        devices = get_devices()
        return len(devices) == 1
    except Exception as exc:
        xbmc.log(
            "[Mira Hybrid] USB-Status: " + str(exc),
            xbmc.LOGWARNING
        )
        return False


def select_source(source):
    """Bewusste Quellenauswahl für diese Kodi-Sitzung merken."""
    source = source.strip().lower()

    if source == "bluetooth":
        HOME.setProperty(LAST_SOURCE_PROPERTY, source)
        target = BT_WINDOW

    elif source == "usb":
        HOME.setProperty(LAST_SOURCE_PROPERTY, source)
        target = USB_WINDOW

    else:
        return

    xbmc.executebuiltin(
        "ActivateWindow({})".format(target)
    )


def open_music():
    """Musikkachel: aktive Quelle vor Benutzerpräferenz."""

    if bluetooth_playing():
        target = BT_WINDOW

    elif kodi_usb_playing():
        target = USB_WINDOW

    else:
        last = HOME.getProperty(
            LAST_SOURCE_PROPERTY
        ).strip().lower()

        connected = usb_connected()

        if last == "bluetooth":
            target = BT_WINDOW

        elif last == "usb" and connected:
            target = USB_WINDOW

        elif connected:
            target = USB_WINDOW

        else:
            target = BT_WINDOW

    xbmc.executebuiltin(
        "ActivateWindow({})".format(target)
    )

# MIRA_HYBRID_ROUTING_R3 END




def radio_playing():
    """Bestehende Mira-Radioerkennung."""

    station = HOME.getProperty(
        "RNSE.RadioStation"
    ).strip()

    return (
        bool(station)
        and xbmc.getCondVisibility("Player.HasMedia")
        and xbmc.getCondVisibility("Player.Playing")
        and not xbmc.getCondVisibility("Player.Paused")
    )


def open_now_playing():
    """Zur tatsächlich laufenden Medienquelle."""

    # Bluetooth hat Vorrang vor einem eventuell
    # noch vorhandenen Kodi-USB-Wiedergabestatus.
    if bluetooth_playing():
        target = BT_WINDOW

    elif kodi_usb_playing():
        target = USB_WINDOW

    elif radio_playing():
        target = RADIO_WINDOW

    else:
        target = SOURCE_WINDOW

    xbmc.executebuiltin(
        "ActivateWindow({})".format(target)
    )

def handle_back():
    """RETURN: zuerst USB-Dateibrowser berücksichtigen."""

    if HOME.getProperty(
        "Mira.USB.BrowserActive"
    ).strip().lower() == "true":
        xbmc.executebuiltin("Action(Back)")
        return


    if xbmc.getCondVisibility(
        "Window.IsActive(1170)"
    ):
        xbmc.executebuiltin(
            "ActivateWindow(10000)"
        )

    else:
        # Bestehende RETURN-Logik beibehalten.
        xbmc.executebuiltin(
            "RunScript("
            "/home/pi/.kodi/userdata/scripts/"
            "radio_player.py,back)"
        )


def main():
    mode = (
        sys.argv[1].lower()
        if len(sys.argv) > 1
        else "open"
    )

    if mode == "open":
        open_music()

    elif mode == "select":
        if len(sys.argv) >= 3:
            select_source(sys.argv[2])

    elif mode == "nowplaying":
        open_now_playing()

    elif mode == "back":
        handle_back()


if __name__ == "__main__":
    main()
