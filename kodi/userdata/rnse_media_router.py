#!/usr/bin/env python3

import json
import sys
import urllib.parse

import xbmc

RADIO_DIRECTORY = (
    "plugin://plugin.audio.radiode/"
    "?data=%7b%22name%22%3a%20%22Local%20stations%22%7d"
    "&mode=get_local_stations"
)


def rpc(method, params=None):
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
    }

    if params is not None:
        request["params"] = params

    response = xbmc.executeJSONRPC(json.dumps(request))
    return json.loads(response)


def decode_radio_data(plugin_url):
    if not plugin_url:
        return None

    if "plugin.audio.radiode" not in plugin_url:
        return None

    try:
        parsed = urllib.parse.urlparse(plugin_url)
        query = urllib.parse.parse_qs(parsed.query)
        raw = query.get("data", [""])[0]

        if not raw:
            return None

        return json.loads(raw)

    except Exception:
        return None


def get_current_radio():
    result = rpc(
        "XBMC.GetInfoLabels",
        {
            "labels": [
                "Player.FilenameAndPath",
            ]
        }
    )

    plugin_url = result.get("result", {}).get(
        "Player.FilenameAndPath",
        ""
    )

    return decode_radio_data(plugin_url)


def get_radio_stations():
    result = rpc(
        "Files.GetDirectory",
        {
            "directory": RADIO_DIRECTORY,
            "media": "music",
            "properties": [
                "title",
                "file",
                "thumbnail",
            ]
        }
    )

    items = result.get("result", {}).get("files", [])

    stations = []

    for item in items:
        plugin_url = item.get("file", "")

        if "mode=play_stream" not in plugin_url:
            continue

        data = decode_radio_data(plugin_url)

        if not data:
            continue

        station_id = data.get("id")

        if not station_id:
            continue

        stations.append(
            {
                "id": station_id,
                "name": data.get("name") or item.get("label", station_id),
                "plugin_url": plugin_url,
            }
        )

    return stations


def switch_radio(direction):
    current = get_current_radio()

    if not current:
        return False

    current_id = current.get("id")

    if not current_id:
        return False

    stations = get_radio_stations()

    if not stations:
        xbmc.log(
            "RNS-E Media Router: keine Radio-Sender gefunden",
            xbmc.LOGWARNING
        )
        return True

    current_index = None

    for index, station in enumerate(stations):
        if station["id"] == current_id:
            current_index = index
            break

    if current_index is None:
        xbmc.log(
            f"RNS-E Media Router: Sender {current_id} nicht gefunden",
            xbmc.LOGWARNING
        )
        return True

    if direction == "next":
        target_index = (current_index + 1) % len(stations)
    else:
        target_index = (current_index - 1) % len(stations)

    current_station = stations[current_index]
    target_station = stations[target_index]

    xbmc.log(
        f"RNS-E Radio: {current_station['name']} -> "
        f"{target_station['name']}",
        xbmc.LOGINFO
    )

    plugin_url = target_station["plugin_url"]

    # Entscheidender Unterschied:
    # Kodi soll den Plugin-Eintrag wirklich ABSPIELEN,
    # nicht als Fenster/Verzeichnis öffnen.
    xbmc.executebuiltin(
        f'PlayMedia("{plugin_url}",1)'
    )

    return True


def generic_switch(direction):
    players = rpc("Player.GetActivePlayers").get("result", [])

    if not players:
        return

    player_id = players[0]["playerid"]

    rpc(
        "Player.GoTo",
        {
            "playerid": player_id,
            "to": "next" if direction == "next" else "previous",
        }
    )


def main():
    if len(sys.argv) < 2:
        return

    direction = sys.argv[1].lower()

    if direction not in ("next", "previous"):
        return

    try:
        if switch_radio(direction):
            return

        generic_switch(direction)

    except Exception as exc:
        xbmc.log(
            f"RNS-E Media Router Fehler: {exc}",
            xbmc.LOGERROR
        )


if __name__ == "__main__":
    main()
