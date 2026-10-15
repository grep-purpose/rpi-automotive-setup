#!/usr/bin/env python3
"""Mira Screenshot-Einstellungen in Kodi."""

import subprocess
import sys

import xbmc
import xbmcgui

QUEUE = "/usr/local/lib/mira/mira_screenshot_queue.py"
PROPERTY = "RNSE.Screenshot.AutoUploadState"


def run_queue(command):
    return subprocess.run(
        ["python3", QUEUE, command],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def synchronize():
    result = run_queue("enabled")

    if result.returncode not in (0, 1):
        raise RuntimeError("Screenshot-Konfiguration nicht lesbar")

    enabled = result.returncode == 0
    value = "on" if enabled else "off"

    xbmc.executebuiltin(
        "Skin.SetString(" + PROPERTY + "," + value + ")"
    )

    return enabled


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "sync"

    if command == "sync":
        synchronize()
        return

    if command == "toggle":
        current = synchronize()
        next_command = "auto-off" if current else "auto-on"

        result = run_queue(next_command)

        if result.returncode != 0:
            raise RuntimeError("Upload-Einstellung fehlgeschlagen")

        synchronize()
        return

    raise ValueError("Unbekannte Aktion")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        xbmc.log(
            "Mira Screenshot Settings: " + repr(exc),
            xbmc.LOGERROR,
        )
        xbmcgui.Dialog().notification(
            "Mira",
            "Screenshot-Einstellung fehlgeschlagen",
            xbmcgui.NOTIFICATION_ERROR,
            3000,
        )
