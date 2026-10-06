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

# Tatsächliche Custom-Window-IDs unserer Player
RNSE_RADIO_WINDOW_ID = 11198
RNSE_MUSIC_WINDOW_ID = 11199

# Radio -> Musik Auto-Switch
_radio_music_switch_candidate_since = 0.0
_radio_music_switch_done = False

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

# ============================================================
# KODI MUSIC -> FIS METADATA EXPORT
# ============================================================

KODI_MUSIC_METADATA_PATH = "/run/user/1000/rnse_kodi_music_metadata.json"
KODI_MUSIC_EXPORT_INTERVAL = 0.75

_last_music_export_time = 0.0
_last_music_export_payload = None



def prop(name, value=""):
    HOME.setProperty(
        PREFIX + name,
        str(value)
    )


def home_prop(name):
    return HOME.getProperty(name)



# RNSE_KODI_MUSIC_FIS_EXPORT_V1

def export_music_metadata(force=False):
    global _last_music_export_time
    global _last_music_export_payload

    now = time.time()

    if (
        not force
        and now - _last_music_export_time
        < KODI_MUSIC_EXPORT_INTERVAL
    ):
        return

    title = home_prop(
        PREFIX + "Title"
    ).strip()

    artist = home_prop(
        PREFIX + "Artist"
    ).strip()

    album = home_prop(
        PREFIX + "Album"
    ).strip()

    source = home_prop(
        PREFIX + "Source"
    ).strip()

    source_label = home_prop(
        PREFIX + "SourceLabel"
    ).strip()

    status = home_prop(
        PREFIX + "Status"
    ).strip()

    active = bool(
        title
        or artist
    )

    payload = {
        "source": "kodi_music",
        "active": active,
        "media_source": (
            source_label
            or source
        ),
        "title": title,
        "artist": artist,
        "album": album,
        "status": status,
        "timestamp": now,
    }

    try:
        target = KODI_MUSIC_METADATA_PATH
        temp = target + ".tmp"

        with open(
            temp,
            "w",
            encoding="utf-8"
        ) as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                separators=(",", ":")
            )

        os.replace(
            temp,
            target
        )

        _last_music_export_time = now
        _last_music_export_payload = payload

    except Exception as exc:
        try:
            xbmc.log(
                "[RNSE Music FIS] Export fehlgeschlagen: "
                + str(exc),
                xbmc.LOGWARNING
            )
        except Exception:
            pass


# RNSE_KODI_MUSIC_FIS_EXPORT_V1 END


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

    export_music_metadata(
        force=True
    )


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

    # BlueZ/busctl liefert Apostrophe teilweise escaped,
    # z.B. Mama\\'s Boy.
    # Für Anzeige, Kodi und FIS soll daraus wieder
    # ein normales Apostroph werden.
    value = value.replace("\\'", "'")

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






# ============================================================
# RNSE ACTIVE APP / AUDIO FOCUS V3
# ============================================================

ACTIVE_APP_PATH = "/run/user/1000/rnse_active_app"

_audio_arbiter_last_bt_playing = False
_audio_arbiter_resume_kodi = False
_audio_arbiter_last_kodi_playing = False

_audio_arbiter_bt_start_position = 0
_audio_arbiter_bt_peak_position = 0
_audio_arbiter_bt_started_at = 0.0

_audio_arbiter_kodi_was_radio = False


def active_app():
    try:
        with open(
            ACTIVE_APP_PATH,
            "r",
            encoding="utf-8"
        ) as handle:

            return handle.read().strip().casefold()

    except Exception:
        return ""


def kodi_is_audio_master():
    return active_app() == "kodi"


def radio_active():
    return bool(
        HOME.getProperty(
            "RNSE.RadioStation"
        ).strip()
    )


def kodi_current_is_radio():

    path = xbmc.getInfoLabel(
        "Player.FilenameAndPath"
    ).strip()

    if "plugin.audio.radiode" in path:
        return True

    direct_stream = HOME.getProperty(
        "RNSE.RadioStreamUrl"
    ).strip()

    return bool(
        direct_stream
        and path == direct_stream
    )


def get_bluetooth_playing(player):

    if not player:
        return False

    status = parse_simple(
        get_property(
            player,
            "Status"
        )
    )

    return (
        str(status or "")
        .strip()
        .casefold()
        == "playing"
    )


def get_bluetooth_position(player):

    if not player:
        return 0

    try:
        value = parse_simple(
            get_property(
                player,
                "Position"
            )
        )

        return max(
            0,
            int(value or 0)
        )

    except Exception:
        return 0


def pause_kodi_for_bluetooth():

    global _audio_arbiter_resume_kodi

    try:

        if xbmc.getCondVisibility(
            "Player.Playing"
        ):

            _audio_arbiter_resume_kodi = True

            xbmc.Player().pause()

            xbmc.log(
                "[RNSE Audio V3] Bluetooth gestartet -> "
                "Kodi vorläufig pausiert",
                xbmc.LOGINFO
            )

    except Exception as exc:

        xbmc.log(
            "[RNSE Audio V3] Kodi-Pause fehlgeschlagen: "
            + str(exc),
            xbmc.LOGWARNING
        )


def resume_kodi_after_temporary_bluetooth():

    global _audio_arbiter_resume_kodi

    if not _audio_arbiter_resume_kodi:
        return

    try:

        if xbmc.getCondVisibility(
            "Player.Paused"
        ):

            xbmc.Player().pause()

            xbmc.log(
                "[RNSE Audio V3] Temporäres Bluetooth beendet -> "
                "Kodi fortgesetzt",
                xbmc.LOGINFO
            )

    except Exception as exc:

        xbmc.log(
            "[RNSE Audio V3] Kodi-Resume fehlgeschlagen: "
            + str(exc),
            xbmc.LOGWARNING
        )

    _audio_arbiter_resume_kodi = False


def stop_old_radio_after_music_switch():

    global _audio_arbiter_resume_kodi

    try:

        if (
            xbmc.getCondVisibility(
                "Player.HasMedia"
            )
            and kodi_current_is_radio()
        ):

            xbmc.Player().stop()

            xbmc.log(
                "[RNSE Audio V3] Echte Bluetooth-Musik erkannt -> "
                "alten Radio-Stream gestoppt",
                xbmc.LOGINFO
            )

    except Exception as exc:

        xbmc.log(
            "[RNSE Audio V3] Radio-Stop fehlgeschlagen: "
            + str(exc),
            xbmc.LOGWARNING
        )

    _audio_arbiter_resume_kodi = False


def reset_audio_focus_v3():

    global _audio_arbiter_resume_kodi
    global _audio_arbiter_bt_start_position
    global _audio_arbiter_bt_peak_position
    global _audio_arbiter_bt_started_at
    global _audio_arbiter_kodi_was_radio

    _audio_arbiter_resume_kodi = False

    _audio_arbiter_bt_start_position = 0
    _audio_arbiter_bt_peak_position = 0
    _audio_arbiter_bt_started_at = 0.0

    _audio_arbiter_kodi_was_radio = False



def radio_to_music_autoswitch(player):
    """
    Wenn im Radio-Player echte Bluetooth-Musik gestartet wird,
    automatisch zum Musik-Player wechseln.

    Nur Radio -> Musik.
    Kein automatischer Rückweg.

    Schutz gegen kurze Smartphone-Töne:
    - Bluetooth muss playing sein
    - ein Titel muss vorhanden sein
    - Zustand muss ca. 1,8 Sekunden stabil bleiben
    """

    global _radio_music_switch_candidate_since
    global _radio_music_switch_done

    # Nur innerhalb von Kodi arbeiten.
    if not kodi_is_audio_master():
        _radio_music_switch_candidate_since = 0.0
        _radio_music_switch_done = False
        return

    try:
        current_window = xbmcgui.getCurrentWindowId()
    except Exception:
        current_window = 0

    # Sobald wir nicht mehr im Radio-Player sind,
    # Kandidatenzustand zurücksetzen.
    if current_window != RNSE_RADIO_WINDOW_ID:
        _radio_music_switch_candidate_since = 0.0

        if not get_bluetooth_playing(player):
            _radio_music_switch_done = False

        return

    bt_playing = get_bluetooth_playing(player)

    title = (
        HOME.getProperty(
            "RNSE.Music.Title"
        )
        .strip()
    )

    # Kein echtes Musiksignal erkennbar.
    if not bt_playing or not title:
        _radio_music_switch_candidate_since = 0.0

        if not bt_playing:
            _radio_music_switch_done = False

        return

    # Für dieselbe laufende Wiedergabe nur einmal wechseln.
    if _radio_music_switch_done:
        return

    now = time.monotonic()

    if _radio_music_switch_candidate_since == 0.0:
        _radio_music_switch_candidate_since = now

        xbmc.log(
            "[RNSE UI] Radio -> Musik Kandidat erkannt: "
            + title,
            xbmc.LOGINFO
        )

        return

    # Kurze Smartphone-Töne ignorieren.
    if (
        now
        - _radio_music_switch_candidate_since
        < 1.8
    ):
        return

    xbmc.log(
        "[RNSE UI] Bluetooth-Musik stabil erkannt -> "
        "wechsle Radio zu Musik",
        xbmc.LOGINFO
    )

    _radio_music_switch_done = True
    _radio_music_switch_candidate_since = 0.0

    xbmc.executebuiltin(
        f"ReplaceWindow({RNSE_MUSIC_WINDOW_ID})"
    )


def audio_arbiter_update(player):
    """
    RNSE Audio Focus V3.

    Grundidee:

    - Bluetooth startet:
      Kodi zunächst nur pausieren.

    - Bluetooth endet sehr schnell:
      System-/Entsperr-/Benachrichtigungston -> Kodi Resume.

    - Bluetooth endet und AVRCP springt auf die alte
      Startposition zurück:
      temporäres Smartphone-Audio, z.B. WhatsApp -> Kodi Resume.

    - Bluetooth endet an der neu erreichten Position:
      echte Musikquelle, z.B. Spotify -> alter Radio-Stream wird
      endgültig gestoppt.

    - Startet Kodi während Bluetooth läuft bewusst neu,
      gewinnt Kodi und Bluetooth wird pausiert.
    """

    global _audio_arbiter_last_bt_playing
    global _audio_arbiter_resume_kodi
    global _audio_arbiter_last_kodi_playing

    global _audio_arbiter_bt_start_position
    global _audio_arbiter_bt_peak_position
    global _audio_arbiter_bt_started_at

    global _audio_arbiter_kodi_was_radio


    # --------------------------------------------------------
    # Nur Kodi darf diesen Arbiter verwenden.
    # HUDIY / Android Auto bleibt vollständig unangetastet.
    # --------------------------------------------------------

    if not kodi_is_audio_master():

        _audio_arbiter_last_bt_playing = False
        _audio_arbiter_last_kodi_playing = False

        reset_audio_focus_v3()
        return


    now = time.monotonic()

    bt_playing = get_bluetooth_playing(
        player
    )

    kodi_playing = bool(
        xbmc.getCondVisibility(
            "Player.Playing"
        )
    )


    bt_started = (
        bt_playing
        and not _audio_arbiter_last_bt_playing
    )

    bt_stopped = (
        not bt_playing
        and _audio_arbiter_last_bt_playing
    )

    kodi_started = (
        kodi_playing
        and not _audio_arbiter_last_kodi_playing
    )


    # --------------------------------------------------------
    # Bluetooth startet.
    #
    # Noch NICHT entscheiden, ob Spotify oder temporäres Audio.
    # Beide sehen am Anfang identisch aus.
    # --------------------------------------------------------

    if bt_started:

        _audio_arbiter_bt_start_position = (
            get_bluetooth_position(
                player
            )
        )

        _audio_arbiter_bt_peak_position = (
            _audio_arbiter_bt_start_position
        )

        _audio_arbiter_bt_started_at = now

        _audio_arbiter_kodi_was_radio = bool(
            kodi_playing
            and kodi_current_is_radio()
        )

        if kodi_playing:
            pause_kodi_for_bluetooth()
            kodi_playing = False

        xbmc.log(
            "[RNSE Audio V3] BT-Start | "
            "position={} | radio={}".format(
                _audio_arbiter_bt_start_position,
                _audio_arbiter_kodi_was_radio
            ),
            xbmc.LOGINFO
        )


    # --------------------------------------------------------
    # Bluetooth läuft:
    # höchste beobachtete AVRCP-Position merken.
    # --------------------------------------------------------

    if (
        bt_playing
        and _audio_arbiter_bt_started_at > 0.0
    ):

        position = get_bluetooth_position(
            player
        )

        if (
            position
            > _audio_arbiter_bt_peak_position
        ):
            _audio_arbiter_bt_peak_position = (
                position
            )


    # --------------------------------------------------------
    # Kodi wurde vom Benutzer bewusst gestartet / resumed,
    # während Bluetooth noch spielt.
    #
    # Kodi gewinnt.
    # --------------------------------------------------------

    if (
        kodi_started
        and bt_playing
        and not bt_started
        and kodi_current_is_radio()
    ):

        try:

            bluetooth_method(
                "Pause"
            )

            xbmc.log(
                "[RNSE Audio V3] Kodi bewusst gestartet -> "
                "Bluetooth pausiert",
                xbmc.LOGINFO
            )

            bt_playing = False

            reset_audio_focus_v3()

        except Exception as exc:

            xbmc.log(
                "[RNSE Audio V3] Bluetooth-Pause fehlgeschlagen: "
                + str(exc),
                xbmc.LOGWARNING
            )


    # --------------------------------------------------------
    # Bluetooth endet.
    #
    # Jetzt können wir unterscheiden:
    #
    # 1. sehr kurzer Ton -> temporär
    #
    # 2. Position während Wiedergabe hochgelaufen,
    #    danach wieder ungefähr auf Startposition zurück
    #    -> temporär (z.B. WhatsApp)
    #
    # 3. Position bleibt am neuen Stand
    #    -> echte Musik (z.B. Spotify)
    # --------------------------------------------------------

    if (
        bt_stopped
        and _audio_arbiter_bt_started_at > 0.0
    ):

        end_position = get_bluetooth_position(
            player
        )

        elapsed_ms = int(
            max(
                0.0,
                now
                - _audio_arbiter_bt_started_at
            )
            * 1000.0
        )

        start_position = (
            _audio_arbiter_bt_start_position
        )

        peak_position = (
            _audio_arbiter_bt_peak_position
        )

        advanced_ms = max(
            0,
            peak_position
            - start_position
        )

        returned_to_start = (
            abs(
                end_position
                - start_position
            )
            <= 1500
        )

        meaningful_advance = (
            advanced_ms
            >= 1500
        )

        short_temporary = (
            elapsed_ms
            <= 1200
        )

        temporary = bool(
            short_temporary
            or (
                returned_to_start
                and meaningful_advance
            )
        )

        xbmc.log(
            "[RNSE Audio V3] BT-Ende | "
            "start={} peak={} end={} "
            "dauer={}ms advance={}ms "
            "temporary={}".format(
                start_position,
                peak_position,
                end_position,
                elapsed_ms,
                advanced_ms,
                temporary
            ),
            xbmc.LOGINFO
        )


        if temporary:

            resume_kodi_after_temporary_bluetooth()

        else:

            if _audio_arbiter_kodi_was_radio:

                stop_old_radio_after_music_switch()

            else:

                _audio_arbiter_resume_kodi = False


        _audio_arbiter_bt_start_position = 0
        _audio_arbiter_bt_peak_position = 0
        _audio_arbiter_bt_started_at = 0.0

        _audio_arbiter_kodi_was_radio = False


    _audio_arbiter_last_bt_playing = (
        bt_playing
    )

    _audio_arbiter_last_kodi_playing = (
        kodi_playing
    )


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

                export_music_metadata()

                kodi_monitor.waitForAbort(
                    POLL_INTERVAL
                )

                continue


            # ----------------------------------------
            # BLUETOOTH
            # ----------------------------------------

            player = get_player_path()

            if player:

                # Radio hat Audio-Priorität:
                # laufendes Bluetooth sofort pausieren.

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

                # Wenn wir gerade im Radio-Player sind und am
                # Smartphone echte Bluetooth-Musik gestartet wird,
                # automatisch auf den Musik-Player wechseln.
                radio_to_music_autoswitch(
                    player
                )

                # Wenn echte Bluetooth-Musik neu startet,
                # pausieren wir eine laufende Kodi-Quelle.
                audio_arbiter_update(
                    player
                )

                export_music_metadata()

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
