#!/usr/bin/env python3

import json
import socket
import time
import urllib.parse

import xbmc
import xbmcgui


HOME = xbmcgui.Window(10000)

COMMAND_HOST = "127.0.0.1"
COMMAND_PORT = 23457

PROPERTIES = (
    "RNSE.RadioStation",
    "RNSE.RadioStationId",
    "RNSE.RadioProvider",
    "RNSE.RadioLogo",
    "RNSE.RadioStreamUrl",
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

            if monitor.waitForAbort(0.05):
                break

    finally:
        command_socket.close()
        clear_properties()


if __name__ == "__main__":
    main()
