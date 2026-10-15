#!/usr/bin/env python3

import sys
import subprocess
import xbmc
import xbmcgui


def main():
    if len(sys.argv) < 2:
        return

    action = sys.argv[1].strip().lower()

    dialog = xbmcgui.Dialog()

    if action == "reboot":
        confirmed = dialog.yesno(
            "Raspberry Pi neu starten",
            "Raspberry Pi wirklich neu starten?"
        )

        if not confirmed:
            return

        dialog.notification(
            "System",
            "Raspberry Pi wird neu gestartet …",
            xbmcgui.NOTIFICATION_INFO,
            2000
        )

        xbmc.sleep(800)

        subprocess.Popen([
            "sudo",
            "/usr/local/bin/rnse-power",
            "reboot"
        ])

    elif action == "poweroff":
        confirmed = dialog.yesno(
            "Raspberry Pi herunterfahren",
            "Raspberry Pi wirklich herunterfahren?"
        )

        if not confirmed:
            return

        dialog.notification(
            "System",
            "Raspberry Pi wird heruntergefahren …",
            xbmcgui.NOTIFICATION_INFO,
            2000
        )

        xbmc.sleep(800)

        subprocess.Popen([
            "sudo",
            "/usr/local/bin/rnse-power",
            "poweroff"
        ])


if __name__ == "__main__":
    main()
