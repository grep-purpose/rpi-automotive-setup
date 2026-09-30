#!/usr/bin/env python3

import json
import os
import socket
import time
import urllib.parse

import xbmc
import xbmcgui


HOME = xbmcgui.Window(10000)

COMMAND_HOST = "127.0.0.1"
COMMAND_PORT = 23457

# RNSE_KODI_FIS_EXPORT_V1
FIS_METADATA_PATH = "/run/user/1000/rnse_kodi_radio_metadata.json"


def write_fis_metadata():
    """
    Exportiert ausschließlich Kodi-Radio-Metadaten.

    WICHTIG:
    Dieser Kodi-Service sendet selbst KEIN CAN.
    Die eigentliche FIS-Ausgabe bleibt vollständig in
    read_from_canbus.py.
    """

    station = HOME.getProperty(
        "RNSE.RadioStation"
    ).strip()

    title = xbmc.getInfoLabel(
        "MusicPlayer.Title"
    ).strip()

    artist = xbmc.getInfoLabel(
        "MusicPlayer.Artist"
    ).strip()

    try:
        playing = bool(
            xbmc.Player().isPlayingAudio()
        )
    except Exception:
        playing = False

    # Nur als Kodi-Radio behandeln, wenn unser Radio-Service
    # tatsächlich einen Sender erkannt hat.
    active = bool(
        playing
        and station
    )

    payload = {
        "source": "kodi_radio",
        "active": active,
        "station": station if active else "",
        "title": title if active else "",
        "artist": artist if active else "",
        "timestamp": time.time(),
    }

    tmp_path = FIS_METADATA_PATH + ".tmp"

    try:
        with open(
            tmp_path,
            "w",
            encoding="utf-8"
        ) as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False
            )

        os.replace(
            tmp_path,
            FIS_METADATA_PATH
        )

    except Exception as exc:
        xbmc.log(
            f"RNS-E FIS Export Fehler: {exc}",
            xbmc.LOGWARNING
        )

PROPERTIES = (
    "RNSE.RadioStation",
    "RNSE.RadioStationId",
    "RNSE.RadioProvider",
    "RNSE.RadioLogo",
    "RNSE.RadioStreamUrl",
)

# RNSE_RADIO_METADATA_DEBUG
DEBUG_LABELS = (
    "Player.Title",
    "Player.Filename",
    "Player.FilenameAndPath",
    "MusicPlayer.Title",
    "MusicPlayer.Artist",
    "MusicPlayer.Album",
    "MusicPlayer.Genre",
)


def get_debug_metadata():
    return tuple(
        (label, xbmc.getInfoLabel(label).strip())
        for label in DEBUG_LABELS
    )


def log_debug_metadata(snapshot):
    station = HOME.getProperty("RNSE.RadioStation").strip()

    xbmc.log(
        "RNS-E RADIO DEBUG | "
        f"Station={station!r} | "
        + " | ".join(
            f"{label}={value!r}"
            for label, value in snapshot
        ),
        xbmc.LOGINFO
    )


def clear_properties():
    for name in PROPERTIES:
        HOME.clearProperty(name)


def decode_radio_data(path):
    if not path:
        return None

    if "plugin.audio.radiode" not in path:
        return None

    try:
        parsed = urllib.parse.urlparse(path)
        query = urllib.parse.parse_qs(parsed.query)

        raw_data = query.get("data", [""])[0]

        if not raw_data:
            return None

        return json.loads(raw_data)

    except Exception as exc:
        xbmc.log(
            f"RNS-E Metadata: radio.de parse error: {exc}",
            xbmc.LOGWARNING
        )
        return None


def update_radio_metadata():
    path = xbmc.getInfoLabel("Player.FilenameAndPath")
    data = decode_radio_data(path)

    if not data:
        # Ein durch den RNS-E-Router gestarteter Direktstream
        # besitzt keine plugin.audio.radiode-URL mehr.
        # Die Senderdaten wurden deshalb bereits vom Router
        # in Window(Home) gespeichert.
        direct_stream = HOME.getProperty(
            "RNSE.RadioStreamUrl"
        ).strip()

        if direct_stream and path == direct_stream:
            return

        clear_properties()
        return

    station_name = str(data.get("name", "")).strip()
    station_id = str(data.get("id", "")).strip()
    station_logo = str(data.get("icon_url", "")).strip()

    HOME.setProperty("RNSE.RadioStation", station_name)
    HOME.setProperty("RNSE.RadioStationId", station_id)
    HOME.setProperty("RNSE.RadioProvider", "radio.de")
    HOME.setProperty("RNSE.RadioLogo", station_logo)
    HOME.setProperty(
        "RNSE.RadioStreamUrl",
        str(data.get("stream_url", "")).strip()
    )


def handle_media_command(command):
    command = command.strip().lower()

    if command not in ("next", "previous"):
        xbmc.log(
            f"RNS-E Media Control: unbekannter Befehl '{command}'",
            xbmc.LOGWARNING
        )
        return

    xbmc.log(
        f"RNS-E Media Control: {command}",
        xbmc.LOGINFO
    )

    xbmc.executebuiltin(
        f"RunScript(/home/pi/.kodi/userdata/rnse_media_router.py,{command})"
    )


def main():
    monitor = xbmc.Monitor()

    xbmc.log(
        "RNS-E Metadata Service gestartet",
        xbmc.LOGINFO
    )

    command_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    command_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    command_socket.bind(
        (COMMAND_HOST, COMMAND_PORT)
    )

    command_socket.setblocking(False)

    xbmc.log(
        f"RNS-E Media Control hört auf UDP {COMMAND_HOST}:{COMMAND_PORT}",
        xbmc.LOGINFO
    )

    last_path = None
    last_metadata_check = 0.0
    last_debug_snapshot = None
    last_debug_check = 0.0

    try:
        while not monitor.abortRequested():

            # ---------------------------------------------------------
            # RNS-E Medienbefehle
            # ---------------------------------------------------------
            while True:
                try:
                    data, _address = command_socket.recvfrom(128)

                except BlockingIOError:
                    break

                try:
                    command = data.decode(
                        "utf-8",
                        errors="ignore"
                    ).strip()

                    handle_media_command(command)

                except Exception as exc:
                    xbmc.log(
                        f"RNS-E Media Control Fehler: {exc}",
                        xbmc.LOGERROR
                    )

            # ---------------------------------------------------------
            # Radio-Metadaten
            # ---------------------------------------------------------
            now = time.monotonic()

            if now - last_metadata_check >= 0.25:
                last_metadata_check = now

                path = xbmc.getInfoLabel(
                    "Player.FilenameAndPath"
                )

                if path != last_path:
                    last_path = path
                    update_radio_metadata()

            # ---------------------------------------------------------
            # Radio-Metadaten Diagnose
            # ---------------------------------------------------------
            if now - last_debug_check >= 0.5:
                last_debug_check = now

                debug_snapshot = get_debug_metadata()

                # Kodi-Radio-Zustand für die zentrale FIS-Pipeline exportieren.
                write_fis_metadata()

                if debug_snapshot != last_debug_snapshot:
                    last_debug_snapshot = debug_snapshot
                    log_debug_metadata(debug_snapshot)

            if monitor.waitForAbort(0.05):
                break

    finally:
        command_socket.close()

        # Keine alten Kodi-Metadaten nach dem Beenden hinterlassen.
        try:
            os.remove(FIS_METADATA_PATH)
        except FileNotFoundError:
            pass
        except Exception:
            pass

        clear_properties()


if __name__ == "__main__":
    main()
