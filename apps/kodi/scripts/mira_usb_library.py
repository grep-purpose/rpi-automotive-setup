#!/usr/bin/env python3
"""Mira USB: gemeinsame Musikbibliothek fuer USB-Medien."""

import json
import sys
from pathlib import Path
from urllib.parse import quote

import xbmc
import xbmcgui

sys.path.insert(0, "/home/pi")
from mira_usb_status import get_devices

BASE = Path("/home/pi/.kodi/userdata/scripts")
HOME = xbmcgui.Window(10000)


def text(value, fallback=""):
    value = str(value or "").strip()
    return value or fallback


def sortkey(value):
    return text(value).casefold()


def load_library():
    devices = get_devices()

    if len(devices) != 1:
        raise RuntimeError(
            "Keine eindeutige USB-Musikquelle"
            if not devices else
            "Mehrere USB-Musikquellen angeschlossen"
        )

    device = devices[0]

    if not device["indexed"] or not device["index"]:
        raise RuntimeError("Musikbibliothek noch nicht erstellt")

    index = json.loads(
        Path(device["index"]).read_text(encoding="utf-8")
    )

    if index.get("uuid") != device["uuid"]:
        raise RuntimeError("Bibliothekskennung stimmt nicht")

    files = index.get("files")

    if not isinstance(files, dict):
        raise RuntimeError("Ungueltige Bibliothek")

    root = Path(device["mount"]).resolve()
    tracks = []

    for relative, record in files.items():
        if not isinstance(record, dict):
            continue

        info = record.get("metadata")

        if not isinstance(info, dict):
            continue

        path = (root / relative).resolve()

        if not path.is_relative_to(root):
            continue

        if not path.is_file():
            continue

        try:
            number = int(info.get("track", 0))
        except (ValueError, TypeError):
            number = 0

        tracks.append({
            "path": str(path),
            "title": text(info.get("title"), path.stem),
            "artist": text(
                info.get("artist"), "Unbekannter Interpret"
            ),
            "album": text(
                info.get("album"), "Unbekanntes Album"
            ),
            "track": number,
        })

    return device, tracks


def play_tracks(songs, selected):
    if not songs:
        return

    position = songs.index(selected)

    # Begrenztes Playlist-Fenster fuer schnellen Start.
    start = max(0, position - 20)
    end = min(len(songs), position + 101)
    chosen = songs[start:end]

    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()

    for song in chosen:
        path = song["path"]
        item = xbmcgui.ListItem(path=path)

        art = "image://music@" + quote(path, safe="") + "/"
        item.setArt({"thumb": art})

        # Wie beim funktionierenden Nano-Prototyp:
        # Metadaten des ausgewaehlten Titels uebergeben.
        if song is selected:
            tag = item.getMusicInfoTag()
            tag.setTitle(song["title"])
            tag.setArtist(song["artist"])
            tag.setAlbum(song["album"])

        playlist.add(path, listitem=item)

    xbmc.Player().play(
        playlist, startpos=position - start
    )

    xbmc.executebuiltin("ActivateWindow(1170)")


class MiraUSBLibrary(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.device = kwargs["device"]
        self.tracks = kwargs["tracks"]
        self.root = Path(self.device["mount"]).resolve()
        self.screen = ("home", None)
        self.history = []
        self.rows = []

    def onInit(self):
        self.list_control = self.getControl(9300)
        self.render()

    def navigate(self, screen):
        position = max(
            0, self.list_control.getSelectedPosition()
        )
        self.history.append((self.screen, position))
        self.screen = screen
        self.render()

    def go_back(self):
        if not self.history:
            self.close()
            return

        self.screen, position = self.history.pop()
        self.render(position)

    def albums_for(self, artist=None):
        groups = {}

        for song in self.tracks:
            if artist is not None and song["artist"] != artist:
                continue

            key = (song["artist"], song["album"])
            groups.setdefault(key, []).append(song)

        return sorted(
            groups.items(),
            key=lambda item: (
                sortkey(item[0][1]),
                sortkey(item[0][0])
            )
        )

    def add(self, title, subtitle="", target=None, playback=None):
        self.rows.append((
            title, subtitle, target, playback
        ))

    def render(self, focus=0):
        kind, data = self.screen
        self.rows = []

        if kind == "home":
            caption = self.device["name"]

            for title, target in (
                ("Interpreten", ("artists", None)),
                ("Alben", ("albums", None)),
                ("Alle Titel", ("titles", None)),
                ("Ordner", ("folders", self.root)),
            ):
                self.add(title, target=target)

        elif kind == "artists":
            caption = "Musik / Interpreten"

            artists = sorted(
                {s["artist"] for s in self.tracks},
                key=sortkey
            )

            for artist in artists:
                self.add(
                    artist,
                    target=("artist_albums", artist)
                )

        elif kind in ("albums", "artist_albums"):
            artist = data if kind == "artist_albums" else None
            caption = (
                "Musik / " + artist
                if artist else "Musik / Alben"
            )

            for (name, album), songs in self.albums_for(artist):
                self.add(
                    album,
                    name,
                    target=("album_tracks", (name, album))
                )

        elif kind == "album_tracks":
            artist, album = data
            caption = "Musik / " + album

            songs = [
                s for s in self.tracks
                if s["artist"] == artist
                and s["album"] == album
            ]

            songs.sort(key=lambda s: (
                s["track"] if s["track"] > 0 else 9999,
                sortkey(s["title"])
            ))

            for song in songs:
                self.add(
                    song["title"],
                    song["artist"],
                    playback=(songs, song)
                )

        elif kind == "titles":
            caption = "Musik / Alle Titel"

            songs = sorted(
                self.tracks,
                key=lambda s: (
                    sortkey(s["title"]),
                    sortkey(s["artist"])
                )
            )

            for song in songs:
                self.add(
                    song["title"],
                    song["artist"] + " · " + song["album"],
                    playback=(songs, song)
                )

        elif kind == "folders":
            folder = Path(data).resolve()

            if not folder.is_relative_to(self.root):
                self.close()
                return

            caption = (
                self.device["name"]
                if folder == self.root
                else "Ordner / " + folder.name
            )

            try:
                directories = sorted(
                    (
                        p for p in folder.iterdir()
                        if p.is_dir()
                        and not p.is_symlink()
                        and not p.name.startswith(".")
                    ),
                    key=lambda p: sortkey(p.name)
                )
            except OSError:
                directories = []

            # Auch Apple-iPod-Ordner bleiben im
            # optionalen echten Ordnerbrowser erreichbar.
            for directory in directories:
                self.add(
                    directory.name,
                    target=("folders", directory)
                )

            songs = sorted(
                (
                    s for s in self.tracks
                    if Path(s["path"]).parent == folder
                ),
                key=lambda s: sortkey(s["title"])
            )

            for song in songs:
                self.add(
                    song["title"],
                    song["artist"] + " · " + song["album"],
                    playback=(songs, song)
                )

        else:
            caption = "USB-Musik"

        self.setProperty("Mira.USB.Path", caption)
        self.list_control.reset()

        items = [
            xbmcgui.ListItem(
                label=title,
                label2=subtitle
            )
            for title, subtitle, target, playback in self.rows
        ]

        if not items:
            items = [
                xbmcgui.ListItem(
                    label="Keine Eintraege vorhanden"
                )
            ]

        self.list_control.addItems(items)
        self.list_control.selectItem(
            min(focus, len(items) - 1)
        )
        self.setFocusId(9300)

    def onClick(self, control_id):
        if control_id != 9300:
            return

        index = self.list_control.getSelectedPosition()

        if not 0 <= index < len(self.rows):
            return

        _, _, target, playback = self.rows[index]

        if target is not None:
            self.navigate(target)
            return

        if playback is not None:
            songs, selected = playback
            self.close()
            play_tracks(songs, selected)

    def onAction(self, action):
        if action.getId() in (9, 10, 92):
            self.go_back()


def main():
    try:
        device, tracks = load_library()

    except Exception as exc:
        xbmc.log(
            "[Mira USB Library] " + str(exc),
            xbmc.LOGERROR
        )
        xbmcgui.Dialog().notification(
            "Mira USB",
            str(exc),
            xbmcgui.NOTIFICATION_WARNING,
            4500
        )
        return

    if not tracks:
        xbmcgui.Dialog().notification(
            "Mira USB",
            "Keine Musikdateien gefunden",
            xbmcgui.NOTIFICATION_WARNING,
            4500
        )
        return

    dialog = MiraUSBLibrary(
        "MiraUSBListV3.xml",
        str(BASE),
        "default",
        "1080i",
        device=device,
        tracks=tracks
    )

    HOME.setProperty("Mira.USB.BrowserActive", "true")

    try:
        dialog.doModal()
    finally:
        HOME.clearProperty("Mira.USB.BrowserActive")
        del dialog


if __name__ == "__main__":
    main()
