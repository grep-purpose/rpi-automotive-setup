#!/usr/bin/env python3
"""Mira USB: gemeinsamen Musikbrowser öffnen."""

import xbmc


def main():
    xbmc.executebuiltin(
        "RunScript("
        "/home/pi/.kodi/userdata/scripts/"
        "mira_usb_library.py)"
    )


if __name__ == "__main__":
    main()
