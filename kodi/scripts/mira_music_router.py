#!/usr/bin/env python3

import sys
from pathlib import Path
from urllib.parse import unquote

import xbmc
import xbmcgui

USB_ROOT = Path("/mnt/ipod")

BT_WINDOW = 11199
USB_WINDOW = 1170
SOURCE_WINDOW = 1165
RADIO_WINDOW = 11198

HOME = xbmcgui.Window(10000)


def kodi_usb_playing():
    """Ist tatsächlich Musik vom iPod aktiv?"""

    try:
        path = unquote(
            xbmc.getInfoLabel(
                "Player.FilenameAndPath"
            )
        )

        if not path:
            return False

        # Nur echte Dateien vom iPod akzeptieren.
        file_path = Path(path)

        if not file_path.is_relative_to(USB_ROOT):
            return False

        return (
            xbmc.getCondVisibility("Player.Playing")
            and not xbmc.getCondVisibility("Player.Paused")
        )

    except Exception:
        return False


def bluetooth_playing():
    """Bluetooth-Status des bestehenden Mira-Monitors."""

    return (
        HOME.getProperty("RNSE.Music.Status")
        .strip()
        .lower() == "playing"
    )


def open_music():
    """Passenden Musikplayer auswählen."""

    if kodi_usb_playing():
        target = USB_WINDOW

    elif bluetooth_playing():
        target = BT_WINDOW

    else:
        target = SOURCE_WINDOW

    xbmc.executebuiltin(
        "ActivateWindow({})".format(target)
    )




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

    if kodi_usb_playing():
        target = USB_WINDOW

    elif radio_playing():
        target = RADIO_WINDOW

    elif bluetooth_playing():
        target = BT_WINDOW

    else:
        target = SOURCE_WINDOW

    xbmc.executebuiltin(
        "ActivateWindow({})".format(target)
    )

def handle_back():
    """RETURN im USB-Player direkt zu Home."""

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

    elif mode == "nowplaying":
        open_now_playing()

    elif mode == "back":
        handle_back()


if __name__ == "__main__":
    main()
