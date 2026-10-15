#!/usr/bin/env python3

import json
from pathlib import Path
from urllib.parse import quote

import xbmc
import xbmcgui

BASE = Path("/home/pi/.kodi/userdata/scripts")
ROOT = Path("/mnt/mira-nano-test")
INDEX = Path("/home/pi/.kodi/userdata/mira/nano_library.json")
UUID = "5215-FBFC"


def sort_text(value):
    return str(value).casefold()


def load_tracks():
    data = json.loads(INDEX.read_text(encoding="utf-8"))

    if data.get("uuid") != UUID:
        raise ValueError("Falsche Bibliothekskennung")

    tracks = data["tracks"]

    if not isinstance(tracks, list):
        raise ValueError("Ungültiger Musikindex")

    root = ROOT.resolve()

    for track in tracks:
        path = Path(track["path"]).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Ungültiger Dateipfad")

    return tracks


def play_tracks(tracks, selected):
    # Kleine Wiedergabeliste für zügigen Start:
    # maximal 20 vorherige und 100 folgende Titel.
    position = tracks.index(selected)
    start = max(0, position - 20)
    end = min(len(tracks), position + 101)
    chosen = tracks[start:end]

    playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
    playlist.clear()

    for track in chosen:
        path = track["path"]

        item = xbmcgui.ListItem(path=path)

        art = "image://music@" + quote(path, safe="") + "/"
        item.setArt({"thumb": art})

        # Kodi 20 erwartet setArtist als String,
        # nicht als Liste.
        if track is selected:
            tag = item.getMusicInfoTag()
            tag.setTitle(str(track["title"]))
            tag.setArtist(str(track["artist"]))
            tag.setAlbum(str(track["album"]))

        playlist.add(path, listitem=item)

    xbmc.Player().play(
        playlist,
        startpos=position - start
    )
    xbmc.executebuiltin("ActivateWindow(1170)")


class MiraNanoLibrary(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tracks = kwargs.get("tracks", [])
        self.screen = ("home", None)
        self.history = []
        self.rows = []

    def onInit(self):
        self.list_control = self.getControl(9300)
        self.render()

    def navigate(self, screen):
        old_index = max(
            0, self.list_control.getSelectedPosition()
        )
        self.history.append((self.screen, old_index))
        self.screen = screen
        self.render()

    def go_back(self):
        if not self.history:
            self.close()
            return

        self.screen, position = self.history.pop()
        self.render(position)

    def albums_for(self, artist=None):
        albums = {}

        for track in self.tracks:
            if artist is not None and track["artist"] != artist:
                continue

            key = (track["artist"], track["album"])
            albums.setdefault(key, []).append(track)

        return sorted(
            albums.items(),
            key=lambda pair: (
                sort_text(pair[0][1]),
                sort_text(pair[0][0])
            )
        )

    def render(self, focus=0):
        kind, data = self.screen
        self.rows = []

        if kind == "home":
            path_label = "iPod Nano / Musik"
            for title, target in (
                ("Interpreten", ("artists", None)),
                ("Alben", ("albums", None)),
                ("Alle Titel", ("titles", None)),
                ("Ordner", ("folders", None)),
            ):
                self.rows.append(
                    (title, "", target, None)
                )

        elif kind == "artists":
            path_label = "Musik / Interpreten"
            artists = sorted(
                set(t["artist"] for t in self.tracks),
                key=sort_text
            )
            for artist in artists:
                self.rows.append((
                    artist, "",
                    ("artist_albums", artist), None
                ))

        elif kind in ("albums", "artist_albums"):
            artist = data if kind == "artist_albums" else None
            path_label = (
                "Musik / " + artist if artist
                else "Musik / Alben"
            )

            for (name, album), songs in self.albums_for(artist):
                self.rows.append((
                    album,
                    name,
                    ("album_tracks", (name, album)),
                    None
                ))

        elif kind == "album_tracks":
            artist, album = data
            path_label = "Musik / " + album
            songs = [
                t for t in self.tracks
                if t["artist"] == artist and t["album"] == album
            ]
            songs.sort(key=lambda t: (
                int(t.get("track", 0)) or 9999,
                sort_text(t["title"])
            ))

            for track in songs:
                self.rows.append((
                    track["title"],
                    track["artist"],
                    None,
                    (songs, track)
                ))

        elif kind == "titles":
            path_label = "Musik / Alle Titel"
            songs = sorted(
                self.tracks, key=lambda t: sort_text(t["title"])
            )
            for track in songs:
                self.rows.append((
                    track["title"],
                    track["artist"] + " · " + track["album"],
                    None,
                    (songs, track)
                ))

        elif kind == "folders":
            self.close()
            xbmc.executebuiltin(
                "RunScript("
                "/home/pi/.kodi/userdata/scripts/"
                "mira_usb_browser.py,nano)"
            )
            return

        self.setProperty("Mira.USB.Path", path_label)

        self.list_control.reset()

        items = [
            xbmcgui.ListItem(label=title, label2=subtitle)
            for title, subtitle, target, play in self.rows
        ]

        if items:
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
            songs, track = playback
            self.close()
            play_tracks(songs, track)

    def onAction(self, action):
        if action.getId() in (9, 10, 92):
            self.go_back()


def main():
    if not INDEX.is_file():
        xbmcgui.Dialog().notification(
            "Mira Nano",
            "Musikbibliothek noch nicht erstellt",
            xbmcgui.NOTIFICATION_WARNING,
            4500
        )
        return

    if not (
        ROOT / "iPod_Control/Music"
    ).is_dir():
        xbmcgui.Dialog().notification(
            "Mira Nano",
            "iPod Nano nicht eingebunden",
            xbmcgui.NOTIFICATION_WARNING,
            4500
        )
        return

    try:
        tracks = load_tracks()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        xbmc.log("[Mira Nano] " + str(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().notification(
            "Mira Nano", "Musikindex fehlerhaft",
            xbmcgui.NOTIFICATION_ERROR, 4500
        )
        return

    dialog = MiraNanoLibrary(
        "MiraUSBListV3.xml",
        str(BASE),
        "default",
        "1080i",
        tracks=tracks
    )

    home = xbmcgui.Window(10000)
    home.setProperty("Mira.USB.BrowserActive", "true")

    try:
        dialog.doModal()
    finally:
        home.clearProperty("Mira.USB.BrowserActive")
        del dialog


if __name__ == "__main__":
    main()
