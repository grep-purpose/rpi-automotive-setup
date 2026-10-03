#!/usr/bin/env python3

import base64
import difflib
import hashlib
import json
import os
import unicodedata
import urllib.parse
import urllib.request
import fcntl
import re
import shlex
import subprocess
import sys
import time

import xbmc
import xbmcgui


MUSIC_WINDOW_ID = 11199

PREFIX = "RNSE.Music."
HOME = xbmcgui.Window(10000)

LOCKFILE = "/tmp/rnse_music_status.lock"

PLAYER_INTERFACE = "org.bluez.MediaPlayer1"

POLL_INTERVAL = 0.5
TRACK_REFRESH_INTERVAL = 2.0

# ============================================================
# SPOTIFY ALBUM ART
# ============================================================

SPOTIFY_CREDENTIALS = "/home/pi/.config/rnse-spotify/credentials"
SPOTIFY_ART_DIR = "/home/pi/.kodi/userdata/rnse_music_art"
SPOTIFY_ART_MAX_BYTES = 500 * 1024 * 1024

_spotify_token = ""
_spotify_token_expiry = 0.0

_spotify_last_track_key = ""
_spotify_last_artwork = ""



_bt_anchor_position = 0
_bt_anchor_time = 0.0
_bt_last_position_poll = 0.0
_bt_last_status = "stopped"


def prop(name, value=""):
    HOME.setProperty(
        PREFIX + name,
        str(value)
    )


def home_prop(name):
    return HOME.getProperty(name)


def normalize(value):
    return " ".join(
        str(value or "")
        .strip()
        .casefold()
        .split()
    )


def clean_album(title, album):
    title = str(title or "").strip()
    album = str(album or "").strip()

    if not album:
        return ""

    if normalize(album) == normalize(title):
        return ""

    return album


def clear_properties():

    defaults = {
        "Connected": "false",
        "Source": "",
        "SourceLabel": "",
        "DeviceName": "",
        "Title": "",
        "Artist": "",
        "Album": "",
        "Artwork": "",
        "Status": "stopped",
        "Position": "0",
        "Duration": "0",
        "PositionText": "--:--",
        "DurationText": "--:--",
        "Progress": "0",
        "PlayPause": "▶",
    }

    for key, value in defaults.items():
        prop(key, value)


def run_busctl(args, timeout=2):

    try:

        result = subprocess.run(
            ["busctl", "--system"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            return ""

        return result.stdout.strip()

    except Exception:
        return ""


def parse_simple(output):

    if not output:
        return None

    try:
        tokens = shlex.split(output)
    except Exception:
        return None

    if len(tokens) < 2:
        return None

    value_type = tokens[0]
    value = tokens[1]

    if value_type in (
        "u", "t", "i", "x", "q", "n"
    ):
        try:
            return int(value)
        except Exception:
            return 0

    return value



def decode_busctl_string(value):

    if not isinstance(value, str):
        return value

    # busctl gibt Nicht-ASCII-Zeichen teilweise als
    # oktale Byte-Escapes aus, z.B.:
    #
    #   \342\200\231  -> UTF-8 E2 80 99 -> ’
    #   \303\244      -> UTF-8 C3 A4    -> ä
    #
    # Wir wandeln nur echte \ddd-Oktalfolgen zurück in Bytes.
    if not re.search(r'\\[0-7]{3}', value):
        return value

    data = bytearray()
    i = 0

    while i < len(value):

        if (
            value[i] == "\\"
            and i + 3 < len(value)
            and all(
                ch in "01234567"
                for ch in value[i + 1:i + 4]
            )
        ):
            try:
                data.append(
                    int(
                        value[i + 1:i + 4],
                        8
                    )
                )
                i += 4
                continue
            except Exception:
                pass

        # Normale Zeichen als UTF-8 übernehmen
        data.extend(
            value[i].encode(
                "utf-8",
                errors="replace"
            )
        )
        i += 1

    try:
        return data.decode(
            "utf-8",
            errors="strict"
        )
    except Exception:
        return data.decode(
            "utf-8",
            errors="replace"
        )


def parse_track(output):

    result = {}

    if not output:
        return result

    try:
        tokens = shlex.split(output)
    except Exception:
        return result

    if len(tokens) < 2:
        return result

    i = 2

    while i + 2 < len(tokens):

        key = tokens[i]
        value_type = tokens[i + 1]
        value = tokens[i + 2]

        if value_type in (
            "u", "t", "i", "x", "q", "n"
        ):
            try:
                value = int(value)
            except Exception:
                value = 0
        else:
            value = decode_busctl_string(
                value
            )

        result[key] = value

        i += 3

    return result


def format_time(milliseconds):

    try:
        milliseconds = max(
            0,
            int(milliseconds)
        )
    except Exception:
        milliseconds = 0

    seconds = milliseconds // 1000

    return (
        f"{seconds // 60}:"
        f"{seconds % 60:02d}"
    )


# ============================================================
# AIRPLAY
# ============================================================

def kodi_label(label):
    try:
        return xbmc.getInfoLabel(
            label
        ).strip()
    except Exception:
        return ""


def airplay_active():

    path = kodi_label(
        "Player.FilenameAndPath"
    )

    if not path.startswith(
        "pipe://"
    ):
        return False

    # Kodi AirTunes/AirPlay verwendet bei uns pipe://
    # und liefert anschließend MusicPlayer-Daten.
    return bool(
        kodi_label("Player.Title")
        or kodi_label("MusicPlayer.Title")
    )


def update_airplay():

    title = (
        kodi_label("MusicPlayer.Title")
        or kodi_label("Player.Title")
    )

    artist = kodi_label(
        "MusicPlayer.Artist"
    )

    album = clean_album(
        title,
        kodi_label(
            "MusicPlayer.Album"
        )
    )

    artwork = (
        kodi_label("MusicPlayer.Cover")
        or kodi_label("Player.Art(thumb)")
    )

    position_text = kodi_label(
        "Player.Time"
    )

    duration_text = kodi_label(
        "Player.Duration"
    )

    progress_text = kodi_label(
        "Player.Progress"
    )

    try:
        progress = int(
            float(progress_text or 0)
        )
    except Exception:
        progress = 0

    progress = max(
        0,
        min(
            100,
            progress
        )
    )

    paused = xbmc.getCondVisibility(
        "Player.Paused"
    )

    phone_name = home_prop(
        "RNSE.Phone.Name"
    ).strip()

    if phone_name:
        source_label = (
            "AirPlay · "
            + phone_name
        )
    else:
        source_label = "AirPlay"

    prop(
        "Connected",
        "true"
    )

    prop(
        "Source",
        "airplay"
    )

    prop(
        "SourceLabel",
        source_label
    )

    prop(
        "DeviceName",
        phone_name
    )

    prop(
        "Title",
        title
    )

    prop(
        "Artist",
        artist
    )

    prop(
        "Album",
        album
    )

    prop(
        "Artwork",
        artwork
    )

    prop(
        "PositionText",
        position_text
    )

    prop(
        "DurationText",
        duration_text
    )

    prop(
        "Progress",
        progress
    )

    prop(
        "Status",
        "paused" if paused else "playing"
    )

    prop(
        "PlayPause",
        "▶" if paused else "Ⅱ"
    )



# RNSE-SPOTIFY-ARTWORK START

def spotify_log(message, level=xbmc.LOGINFO):
    try:
        xbmc.log(
            "[RNSE Spotify Artwork] " + str(message),
            level
        )
    except Exception:
        pass


def spotify_normalize(value):
    value = str(value or "").strip().casefold()

    value = unicodedata.normalize(
        "NFKD",
        value
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    return " ".join(
        value.split()
    )


def spotify_track_key(title, artist, album):
    raw = "\x1f".join(
        [
            spotify_normalize(title),
            spotify_normalize(artist),
            spotify_normalize(album),
        ]
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def spotify_load_credentials():
    values = {}

    try:
        with open(
            SPOTIFY_CREDENTIALS,
            "r",
            encoding="utf-8"
        ) as handle:

            for line in handle:
                line = line.strip()

                if (
                    not line
                    or "=" not in line
                ):
                    continue

                key, value = line.split(
                    "=",
                    1
                )

                values[key.strip()] = (
                    value.strip()
                )

    except Exception as exc:
        spotify_log(
            "Zugangsdaten nicht lesbar: "
            + str(exc),
            xbmc.LOGWARNING
        )

    return (
        values.get(
            "SPOTIFY_CLIENT_ID",
            ""
        ),
        values.get(
            "SPOTIFY_CLIENT_SECRET",
            ""
        ),
    )


def spotify_get_token():
    global _spotify_token
    global _spotify_token_expiry

    now = time.time()

    if (
        _spotify_token
        and now
        < _spotify_token_expiry - 30
    ):
        return _spotify_token

    client_id, client_secret = (
        spotify_load_credentials()
    )

    if (
        not client_id
        or not client_secret
    ):
        return ""

    basic = base64.b64encode(
        (
            client_id
            + ":"
            + client_secret
        ).encode("utf-8")
    ).decode("ascii")

    request = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=urllib.parse.urlencode(
            {
                "grant_type":
                    "client_credentials"
            }
        ).encode("utf-8"),
        headers={
            "Authorization":
                "Basic " + basic,
            "Content-Type":
                "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=6
        ) as response:

            data = json.load(
                response
            )

        _spotify_token = str(
            data.get(
                "access_token",
                ""
            )
        )

        expires_in = int(
            data.get(
                "expires_in",
                3600
            )
            or 3600
        )

        _spotify_token_expiry = (
            now + expires_in
        )

        return _spotify_token

    except Exception as exc:
        spotify_log(
            "Token-Fehler: "
            + str(exc),
            xbmc.LOGWARNING
        )

        return ""


def spotify_similarity(left, right):
    left = spotify_normalize(left)
    right = spotify_normalize(right)

    if not left or not right:
        return 0.0

    if left == right:
        return 1.0

    return difflib.SequenceMatcher(
        None,
        left,
        right
    ).ratio()


def spotify_find_best_track(
    token,
    title,
    artist,
    album
):
    clean_title = str(
        title or ""
    ).replace('"', " ")

    clean_artist = str(
        artist or ""
    ).replace('"', " ")

    query = (
        f'track:"{clean_title}" '
        f'artist:"{clean_artist}"'
    )

    url = (
        "https://api.spotify.com/v1/search?"
        + urllib.parse.urlencode(
            {
                "q": query,
                "type": "track",
                "limit": 5,
            }
        )
    )

    request = urllib.request.Request(
        url,
        headers={
            "Authorization":
                "Bearer " + token,
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=7
        ) as response:

            data = json.load(
                response
            )

    except Exception as exc:
        spotify_log(
            "Suchfehler: "
            + str(exc),
            xbmc.LOGWARNING
        )

        return None

    items = (
        data
        .get("tracks", {})
        .get("items", [])
    )

    best = None
    best_score = 0.0

    for item in items:

        candidate_title = str(
            item.get(
                "name",
                ""
            )
            or ""
        )

        candidate_artists = [
            str(
                entry.get(
                    "name",
                    ""
                )
                or ""
            )
            for entry
            in item.get(
                "artists",
                []
            )
        ]

        candidate_artist_joined = (
            ", ".join(
                candidate_artists
            )
        )

        candidate_album = str(
            item.get(
                "album",
                {}
            ).get(
                "name",
                ""
            )
            or ""
        )

        title_score = (
            spotify_similarity(
                title,
                candidate_title
            )
        )

        artist_scores = [
            spotify_similarity(
                artist,
                candidate_artist_joined
            )
        ]

        artist_scores.extend(
            spotify_similarity(
                artist,
                candidate
            )
            for candidate
            in candidate_artists
        )

        artist_score = max(
            artist_scores
            or [0.0]
        )

        album_score = (
            spotify_similarity(
                album,
                candidate_album
            )
            if album
            else 1.0
        )

        score = (
            title_score * 0.60
            + artist_score * 0.35
            + album_score * 0.05
        )

        # Lieber kein Cover als ein offensichtlich falsches.
        if title_score < 0.70:
            continue

        if artist_score < 0.65:
            continue

        if score > best_score:
            best = item
            best_score = score

    if best is not None:
        spotify_log(
            "Treffer: "
            + str(
                best.get(
                    "name",
                    ""
                )
            )
            + " | Score "
            + f"{best_score:.2f}"
        )

    else:
        spotify_log(
            "Kein ausreichend sicherer Treffer für "
            + title
            + " / "
            + artist
        )

    return best


def spotify_existing_artwork(key):
    for extension in (
        "jpg",
        "png",
        "webp"
    ):
        path = os.path.join(
            SPOTIFY_ART_DIR,
            key + "." + extension
        )

        if os.path.isfile(path):
            try:
                os.utime(
                    path,
                    None
                )
            except Exception:
                pass

            return path

    return ""


def spotify_detect_extension(data):
    if data.startswith(
        b"\xff\xd8\xff"
    ):
        return "jpg"

    if data.startswith(
        b"\x89PNG\r\n\x1a\n"
    ):
        return "png"

    if (
        len(data) >= 12
        and data[:4] == b"RIFF"
        and data[8:12] == b"WEBP"
    ):
        return "webp"

    return ""


def spotify_prune_cache():
    try:
        os.makedirs(
            SPOTIFY_ART_DIR,
            exist_ok=True
        )

        files = []

        for name in os.listdir(
            SPOTIFY_ART_DIR
        ):
            path = os.path.join(
                SPOTIFY_ART_DIR,
                name
            )

            if not os.path.isfile(path):
                continue

            try:
                stat = os.stat(path)
            except Exception:
                continue

            files.append(
                (
                    stat.st_mtime,
                    stat.st_size,
                    path
                )
            )

        total = sum(
            size
            for _, size, _
            in files
        )

        if total <= SPOTIFY_ART_MAX_BYTES:
            return

        files.sort(
            key=lambda entry:
                entry[0]
        )

        for _, size, path in files:

            if total <= SPOTIFY_ART_MAX_BYTES:
                break

            try:
                os.remove(path)
                total -= size
            except Exception:
                pass

    except Exception as exc:
        spotify_log(
            "Cache-Cleanup fehlgeschlagen: "
            + str(exc),
            xbmc.LOGWARNING
        )


def spotify_download_artwork(
    image_url,
    key
):
    if not image_url:
        return ""

    try:
        os.makedirs(
            SPOTIFY_ART_DIR,
            exist_ok=True
        )

        request = urllib.request.Request(
            image_url,
            headers={
                "User-Agent":
                    "RNS-E-RaspberryPi-Automotive/1.0"
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:

            data = response.read()

        if not data:
            return ""

        extension = (
            spotify_detect_extension(
                data
            )
        )

        if not extension:
            spotify_log(
                "Unbekanntes Bildformat",
                xbmc.LOGWARNING
            )
            return ""

        final_path = os.path.join(
            SPOTIFY_ART_DIR,
            key + "." + extension
        )

        temp_path = (
            final_path + ".tmp"
        )

        with open(
            temp_path,
            "wb"
        ) as handle:
            handle.write(data)

        os.replace(
            temp_path,
            final_path
        )

        spotify_prune_cache()

        spotify_log(
            "Cover gespeichert: "
            + final_path
        )

        return final_path

    except Exception as exc:
        spotify_log(
            "Cover-Download fehlgeschlagen: "
            + str(exc),
            xbmc.LOGWARNING
        )

        return ""


def spotify_artwork_for_track(
    title,
    artist,
    album
):
    global _spotify_last_track_key
    global _spotify_last_artwork

    if not title or not artist:
        _spotify_last_track_key = ""
        _spotify_last_artwork = ""
        return ""

    key = spotify_track_key(
        title,
        artist,
        album
    )

    # Gleicher Track wie beim letzten Refresh:
    # keinerlei Netzwerkzugriff.
    if key == _spotify_last_track_key:
        return _spotify_last_artwork

    _spotify_last_track_key = key
    _spotify_last_artwork = ""

    cached = spotify_existing_artwork(
        key
    )

    if cached:
        spotify_log(
            "Cache-Treffer: "
            + cached
        )

        _spotify_last_artwork = cached
        return cached

    token = spotify_get_token()

    if not token:
        return ""

    track = spotify_find_best_track(
        token,
        title,
        artist,
        album
    )

    if not track:
        return ""

    images = (
        track
        .get("album", {})
        .get("images", [])
    )

    if not images:
        return ""

    image_url = str(
        images[0].get(
            "url",
            ""
        )
        or ""
    )

    artwork = spotify_download_artwork(
        image_url,
        key
    )

    _spotify_last_artwork = artwork

    return artwork

# RNSE-SPOTIFY-ARTWORK END


# ============================================================
# BLUETOOTH / BLUEZ
# ============================================================

def get_player_path():

    output = run_busctl(
        [
            "tree",
            "org.bluez"
        ]
    )

    if not output:
        return ""

    match = re.search(
        r'(/org/bluez/\S+/player\d+)',
        output
    )

    if not match:
        return ""

    return match.group(1)


def get_property(player, name):

    return run_busctl(
        [
            "get-property",
            "org.bluez",
            player,
            PLAYER_INTERFACE,
            name,
        ]
    )


def get_device_name(player):

    if not player:
        return ""

    device_path = player.rsplit(
        "/player",
        1
    )[0]

    output = run_busctl(
        [
            "get-property",
            "org.bluez",
            device_path,
            "org.bluez.Device1",
            "Alias",
        ]
    )

    value = parse_simple(
        output
    )

    return str(
        value or ""
    ).strip()


def update_bluetooth_metadata(player):

    track = parse_track(
        get_property(
            player,
            "Track"
        )
    )

    title = str(
        track.get(
            "Title",
            ""
        ) or ""
    ).strip()

    artist = str(
        track.get(
            "Artist",
            ""
        ) or ""
    ).strip()

    album = clean_album(
        title,
        track.get(
            "Album",
            ""
        )
    )

    try:
        duration = int(
            track.get(
                "Duration",
                0
            ) or 0
        )
    except Exception:
        duration = 0

    prop(
        "Title",
        title
    )

    prop(
        "Artist",
        artist
    )

    prop(
        "Album",
        album
    )

    artwork = spotify_artwork_for_track(
        title,
        artist,
        album
    )

    prop(
        "Artwork",
        artwork
    )


    prop(
        "Duration",
        duration
    )

    prop(
        "DurationText",
        format_time(
            duration
        )
    )

    return duration


def update_bluetooth_live(
    player,
    duration
):

    global _bt_anchor_position
    global _bt_anchor_time
    global _bt_last_position_poll
    global _bt_last_status

    now = time.monotonic()

    status = parse_simple(
        get_property(
            player,
            "Status"
        )
    )

    status = str(
        status or "stopped"
    )

    if (
        _bt_anchor_time == 0.0
        or status != _bt_last_status
        or now - _bt_last_position_poll >= 1.5
    ):

        value = parse_simple(
            get_property(
                player,
                "Position"
            )
        )

        try:
            bluez_position = int(
                value or 0
            )
        except Exception:
            bluez_position = 0

        if _bt_anchor_time == 0.0:

            _bt_anchor_position = (
                bluez_position
            )

            _bt_anchor_time = now

        else:

            if _bt_last_status == "playing":

                predicted = (
                    _bt_anchor_position
                    + int(
                        (
                            now
                            - _bt_anchor_time
                        )
                        * 1000
                    )
                )

            else:

                predicted = (
                    _bt_anchor_position
                )

            difference = (
                bluez_position
                - predicted
            )

            if (
                status != "playing"
                or bluez_position
                    > _bt_anchor_position
                or abs(difference)
                    > 5000
            ):

                _bt_anchor_position = (
                    bluez_position
                )

                _bt_anchor_time = now

        _bt_last_position_poll = now


    if status == "playing":

        position = (
            _bt_anchor_position
            + int(
                (
                    now
                    - _bt_anchor_time
                )
                * 1000
            )
        )

    else:

        position = (
            _bt_anchor_position
        )


    if duration > 0:

        position = min(
            position,
            duration
        )

        progress = int(
            round(
                float(position)
                / float(duration)
                * 100.0
            )
        )

    else:

        progress = 0


    progress = max(
        0,
        min(
            100,
            progress
        )
    )


    device_name = get_device_name(
        player
    )

    if device_name:

        source_label = (
            "Bluetooth · "
            + device_name
        )

    else:

        source_label = (
            "Bluetooth"
        )


    prop(
        "Connected",
        "true"
    )

    prop(
        "Source",
        "bluetooth"
    )

    prop(
        "SourceLabel",
        source_label
    )

    prop(
        "DeviceName",
        device_name
    )

    prop(
        "Position",
        position
    )

    prop(
        "PositionText",
        format_time(
            position
        )
    )

    prop(
        "Status",
        status
    )

    prop(
        "Progress",
        progress
    )

    prop(
        "PlayPause",
        "Ⅱ"
        if status == "playing"
        else "▶"
    )

    _bt_last_status = status


# ============================================================
# STEUERUNG
# ============================================================

def active_source():

    if airplay_active():
        return "airplay"

    if get_player_path():
        return "bluetooth"

    return ""


def bluetooth_method(method):

    player = get_player_path()

    if not player:
        return

    run_busctl(
        [
            "call",
            "org.bluez",
            player,
            PLAYER_INTERFACE,
            method,
        ]
    )


def media_method(method):

    source = active_source()

    if source == "airplay":

        mapping = {
            "Play": "PlayerControl(Play)",
            "Pause": "PlayerControl(Play)",
            "Next": "PlayerControl(Next)",
            "Previous": "PlayerControl(Previous)",
        }

        action = mapping.get(
            method
        )

        if action:
            xbmc.executebuiltin(
                action
            )

        return

    if source == "bluetooth":
        bluetooth_method(
            method
        )
        return


def toggle_play_pause():

    source = active_source()

    if source == "airplay":

        xbmc.Player().pause()
        return

    if source == "bluetooth":

        player = get_player_path()

        if not player:
            return

        status = parse_simple(
            get_property(
                player,
                "Status"
            )
        )

        if status == "playing":
            bluetooth_method(
                "Pause"
            )
        else:
            bluetooth_method(
                "Play"
            )


# ============================================================
# MONITOR
# ============================================================

def acquire_lock():

    handle = open(
        LOCKFILE,
        "w"
    )

    try:

        fcntl.flock(
            handle,
            fcntl.LOCK_EX
            | fcntl.LOCK_NB
        )

        return handle

    except BlockingIOError:

        handle.close()
        return None


def music_window_active():

    try:
        return (
            xbmcgui.getCurrentWindowId()
            == MUSIC_WINDOW_ID
        )
    except Exception:
        return False


def monitor():

    lock = acquire_lock()

    if lock is None:
        return

    kodi_monitor = xbmc.Monitor()



    duration = 0
    last_track_refresh = 0.0

    try:

        while (
            not kodi_monitor.abortRequested()
        ):



            # ----------------------------------------
            # AIRPLAY hat Priorität
            # ----------------------------------------

            if airplay_active():

                update_airplay()

                kodi_monitor.waitForAbort(
                    POLL_INTERVAL
                )

                continue


            # ----------------------------------------
            # BLUETOOTH
            # ----------------------------------------

            player = get_player_path()

            if player:

                now = time.time()

                if (
                    now
                    - last_track_refresh
                    >= TRACK_REFRESH_INTERVAL
                ):

                    duration = (
                        update_bluetooth_metadata(
                            player
                        )
                    )

                    last_track_refresh = now

                update_bluetooth_live(
                    player,
                    duration
                )

            else:

                clear_properties()


            kodi_monitor.waitForAbort(
                POLL_INTERVAL
            )


    finally:

        try:
            fcntl.flock(
                lock,
                fcntl.LOCK_UN
            )
        except Exception:
            pass

        lock.close()


def main():

    mode = (
        sys.argv[1].lower()
        if len(sys.argv) > 1
        else "monitor"
    )

    if mode == "monitor":
        monitor()

    elif mode == "toggle":
        toggle_play_pause()

    elif mode == "play":
        media_method("Play")

    elif mode == "pause":
        media_method("Pause")

    elif mode == "next":
        media_method("Next")

    elif mode == "previous":
        media_method("Previous")


if __name__ == "__main__":
    main()
