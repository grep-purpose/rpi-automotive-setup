from urllib.parse import quote
#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

import xbmc
import xbmcgui

ROOT = Path("/mnt/ipod")
STATE = Path("/tmp/mira_usb_browser_state.json")
HOME = xbmcgui.Window(10000)
EXT = {".mp3", ".flac", ".m4a", ".ogg", ".wav", ".aac"}
HIDDEN = {
    "system volume information", ".rockbox",
    ".spotlight-v100", ".trashes",
    "$recycle.bin", "ipod_control", ".fseventsd"
}

def inside(path):
    try:
        return os.path.commonpath(
            [str(ROOT.resolve()), str(Path(path).resolve())]
        ) == str(ROOT.resolve())
    except (ValueError, OSError):
        return False

def entries(folder):
    found = []
    try:
        for p in folder.iterdir():
            if p.name.startswith(".") or p.name.casefold() in HIDDEN:
                continue
            if not inside(p):
                continue
            if p.is_dir() or (p.is_file() and p.suffix.lower() in EXT):
                found.append(p)
    except OSError:
        pass
    return sorted(found, key=lambda p: (not p.is_dir(), p.name.casefold()))

def read_state():
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
        folder = Path(state["folder"])
        offset = max(0, int(state.get("offset", 0)))
        if folder.is_dir() and inside(folder):
            return folder, offset
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return ROOT, 0

def save_state(folder, offset):
    STATE.write_text(
        json.dumps({"folder": str(folder), "offset": offset}),
        encoding="utf-8"
    )

def render(folder, offset=0):
    items = entries(folder)
    offset = min(max(0, offset), max(0, len(items) - 1))
    save_state(folder, offset)
    rel = folder.relative_to(ROOT)
    HOME.setProperty(
        "Mira.USB.Folder", "/" if str(rel) == "." else "/" + str(rel)
    )
    for i in range(5):
        index = offset + i
        value = ""
        if index < len(items):
            item = items[index]
            value = ("[Ordner]  " if item.is_dir() else "[Musik]  ") + (
                item.name if item.is_dir() else item.stem
            )
        HOME.setProperty(f"Mira.USB.Row{i+1}", value)



def play_selected_usb_file(folder, selected):
    """Bestehende Playlist-Logik inklusive Cover-Fix."""

    from urllib.parse import quote

    tracks = [
        entry for entry in entries(folder)
        if entry.is_file()
    ]

    if selected not in tracks:
        return

    position = tracks.index(selected)

    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()

    for track in tracks:
        art_url = (
            "image://music@"
            + quote(str(track), safe="")
            + "/"
        )

        playlist_item = xbmcgui.ListItem(
            path=str(track)
        )

        playlist_item.setArt({
            "thumb": art_url
        })

        playlist.add(
            str(track),
            listitem=playlist_item
        )

    xbmc.Player().play(
        playlist,
        startpos=position
    )

    xbmc.executebuiltin(
        "ActivateWindow(1170)"
    )


class MiraUSBListV3(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.folder = ROOT
        self.files = []

    def onInit(self):
        self.list_control = self.getControl(9300)
        self.show_folder()

    def show_folder(self):
        self.files = entries(self.folder)

        self.setProperty(
            "Mira.USB.Path",
            "/" if self.folder == ROOT
            else "/" + str(self.folder.relative_to(ROOT))
        )

        self.list_control.reset()

        items = []

        for path in self.files:
            if path.is_dir():
                label = "[Ordner]   " + path.name
            else:
                label = "[Musik]   " + path.stem

            items.append(
                xbmcgui.ListItem(label=label)
            )

        if items:
            self.list_control.addItems(items)
            self.list_control.selectItem(0)

        self.setFocusId(9300)

    def onClick(self, control_id):
        if control_id != 9300:
            return

        index = self.list_control.getSelectedPosition()

        if index < 0 or index >= len(self.files):
            return

        selected = self.files[index]

        if selected.is_dir():
            if inside(selected):
                self.folder = selected
                self.show_folder()
            return

        if selected.is_file() and inside(selected):
            self.close()
            play_selected_usb_file(
                self.folder,
                selected
            )

    def onAction(self, action):
        action_id = action.getId()

        if action_id in (9, 10, 92):
            if self.folder == ROOT:
                self.close()
            else:
                self.folder = self.folder.parent
                self.show_folder()


def open_mira_usb_list():
    dialog = MiraUSBListV3(
        "MiraUSBListV3.xml",
        str(Path(__file__).resolve().parent),
        "default",
        "1080i"
    )

    HOME.setProperty(
        "Mira.USB.BrowserActive",
        "true"
    )

    try:
        dialog.doModal()
    finally:
        HOME.clearProperty(
            "Mira.USB.BrowserActive"
        )
        del dialog



def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "open"

    if mode == "open":
        if not os.path.ismount(ROOT):
            xbmcgui.Dialog().notification(
                "Mira USB", "iPod nicht eingebunden",
                xbmcgui.NOTIFICATION_WARNING, 4000
            )
            return
        open_mira_usb_list()
        return

    folder, offset = read_state()

    if mode == "back":
        if folder == ROOT:
            xbmc.executebuiltin("Dialog.Close(1166)")
        else:
            render(folder.parent)
            xbmc.executebuiltin("SetFocus(9301)")
        return

    if mode == "next":
        render(folder, offset + 5)
        xbmc.executebuiltin("SetFocus(9301)")
        return

    if mode == "previous":
        render(folder, max(0, offset - 5))
        xbmc.executebuiltin("SetFocus(9301)")
        return

    if mode == "select" and len(sys.argv) > 2:
        try:
            index = offset + int(sys.argv[2]) - 1
            item = entries(folder)[index]
        except (ValueError, IndexError):
            return

        if item.is_dir():
            render(item)
            xbmc.executebuiltin("SetFocus(9301)")
        elif item.is_file() and inside(item):
            tracks = [
                entry for entry in entries(folder)
                if entry.is_file()
            ]

            if not tracks:
                return

            playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
            playlist.clear()

            for track in tracks:
                # Cover direkt aus der Musikdatei referenzieren.
                art_url = (
                    "image://music@"
                    + quote(str(track), safe="")
                    + "/"
                )

                playlist_item = xbmcgui.ListItem(
                    path=str(track)
                )

                playlist_item.setArt({
                    "thumb": art_url
                })

                playlist.add(
                    str(track),
                    listitem=playlist_item
                )

            position = tracks.index(item)

            xbmc.executebuiltin("Dialog.Close(1166)")
            xbmc.Player().play(playlist, startpos=position)
            xbmc.executebuiltin("ActivateWindow(1170)")

if __name__ == "__main__":
    main()
