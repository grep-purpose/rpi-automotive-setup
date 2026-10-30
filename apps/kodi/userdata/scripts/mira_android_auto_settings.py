#!/usr/bin/env python3
"""MIRA: change only HUDIY's Android Auto DPI while HUDIY is stopped."""

import fcntl
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from datetime import datetime

import xbmc
import xbmcgui

VALUES = tuple(range(140, 201, 10))
PROPERTY = "RNSE.AndroidAuto.DPI"
CONFIG = Path.home() / ".hudiy/share/config/main_configuration.json"


def read_config(path):
    raw = path.read_bytes()
    data = json.loads(raw)
    aa = data.get("androidAuto")
    if not isinstance(aa, dict):
        raise ValueError("Android-Auto-Konfiguration fehlt")
    dpi = aa.get("dpi")
    if type(dpi) is not int or dpi <= 0:
        raise ValueError("Ungültiger gespeicherter DPI-Wert")
    return raw, data


def hudiy_running():
    result = subprocess.run(
        ["pgrep", "-x", "hudiy"], capture_output=True, timeout=5
    )
    if result.returncode not in (0, 1):
        raise RuntimeError("HUDIY-Prozessstatus konnte nicht geprüft werden")
    return result.returncode == 0


def synchronize(path=None):
    path = CONFIG if path is None else path
    _, data = read_config(path)
    dpi = data["androidAuto"]["dpi"]
    xbmcgui.Window(10000).setProperty(PROPERTY, str(dpi))
    return dpi


class DPIWindow(xbmcgui.WindowXMLDialog):
    """Modal selection using MIRA's USB confirmation dialog design."""

    def configure(self, current):
        self.current = current
        self.value = None

    def onInit(self):
        control = self.getControl(9500)
        control.reset()
        for value in VALUES:
            item = xbmcgui.ListItem(
                label=str(value) + " DPI",
                label2="Aktuell" if value == self.current else "",
            )
            control.addItem(item)
        self.setFocusId(9500)
        control.selectItem(VALUES.index(self.current) if self.current in VALUES else 0)

    def onClick(self, control_id):
        if control_id == 9500:
            index = self.getControl(9500).getSelectedPosition()
            if 0 <= index < len(VALUES):
                self.value = VALUES[index]
                self.close()

    def onAction(self, action):
        if action.getId() in (9, 10, 92):
            self.value = None
            self.close()


def choose_dpi(current):
    dialog = DPIWindow(
        "MiraAndroidAutoDPI.xml", str(Path(__file__).resolve().parent),
        "default", "1080i",
    )
    dialog.configure(current)
    try:
        dialog.doModal()
        return dialog.value
    finally:
        del dialog


def save_dpi(path, value, previous_dpi):
    if type(value) is not int or value not in VALUES:
        raise ValueError("DPI müssen zwischen 140 und 200 in Zehnerschritten liegen")
    if hudiy_running():
        raise RuntimeError("HUDIY läuft noch. Bitte zuerst zu MIRA zurückkehren.")
    if path.is_symlink():
        raise RuntimeError("Verknüpfte Konfiguration: Änderung sicherheitshalber abgebrochen")
    raw, data = read_config(path)
    if data["androidAuto"]["dpi"] != previous_dpi:
        raise RuntimeError("DPI wurden zwischenzeitlich geändert. Auswahl erneut öffnen.")
    if value == previous_dpi:
        return False
    original_mode = stat.S_IMODE(path.stat().st_mode)
    data["androidAuto"]["dpi"] = value
    payload = (json.dumps(data, indent=4, ensure_ascii=False) + "\n").encode()
    assert json.loads(payload) == data

    backups = path.parent / "mira-dpi-backups"
    backups.mkdir(mode=0o700, exist_ok=True)
    backup = backups / ("main_configuration-" +
                        datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".json")
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

    fd, name = tempfile.mkstemp(prefix=".mira-dpi-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchmod(stream.fileno(), original_mode)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # Recheck after writing the temporary file; preserve concurrent edits.
        if hudiy_running() or path.read_bytes() != raw:
            raise RuntimeError("HUDIY oder Konfiguration wurde aktiv. Bitte erneut versuchen.")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "select"
    if command == "sync":
        synchronize()
        return
    if command != "select":
        raise ValueError("Unbekannte Aktion")

    # A modal window may outlive a skin reload. Never hold a file lock
    # across doModal(): a hidden old window must not block future openings.
    if hudiy_running():
        raise RuntimeError("HUDIY läuft noch. Bitte zuerst zu MIRA zurückkehren.")
    current = synchronize()
    value = choose_dpi(current)
    if value is None:
        return

    # Serialize only the brief configuration update, with explicit unlock.
    lock_path = CONFIG.parent / ".mira-dpi.lock"
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("DPI-Speicherung ist belegt. Bitte erneut versuchen.")
        try:
            changed = save_dpi(CONFIG, value, current)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
    synchronize()
    if changed:
        xbmcgui.Dialog().notification(
            "Android Auto",
            str(value) + " DPI · Wirksam beim nächsten Start",
            xbmcgui.NOTIFICATION_INFO, 3500,
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        xbmc.log("MIRA Android Auto Settings: " + repr(exc), xbmc.LOGERROR)
        xbmcgui.Window(10000).clearProperty(PROPERTY)
        xbmcgui.Dialog().notification(
            "Android Auto", str(exc), xbmcgui.NOTIFICATION_ERROR, 5000
        )
