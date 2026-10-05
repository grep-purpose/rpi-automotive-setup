import sys
import xbmc
import xbmcgui

HOME = xbmcgui.Window(10000)

RADIO_WINDOW = 1198

LIST_REQUEST_PROPERTY = "RNSE.Radio.ListRequested"
LIST_WATCH_PROPERTY = "RNSE.Radio.ListWatch"

OLD_PATH_PROPERTY = "RNSE.Radio.ListOldPath"
OLD_ID_PROPERTY = "RNSE.Radio.ListOldId"
OLD_STATION_PROPERTY = "RNSE.Radio.ListOldStation"
OLD_STREAM_PROPERTY = "RNSE.Radio.ListOldStream"


def get_playing_file():

    try:
        if xbmc.Player().isPlaying():
            return xbmc.Player().getPlayingFile().strip()
    except Exception:
        pass

    return ""


def radio_active():

    station = HOME.getProperty(
        "RNSE.RadioStation"
    ).strip()

    return (
        bool(station)
        and xbmc.getCondVisibility(
            "Player.HasMedia"
        )
    )


def clear_list_state():

    for name in (
        LIST_REQUEST_PROPERTY,
        LIST_WATCH_PROPERTY,
        OLD_PATH_PROPERTY,
        OLD_ID_PROPERTY,
        OLD_STATION_PROPERTY,
        OLD_STREAM_PROPERTY,
    ):
        HOME.clearProperty(name)


def focus_first_real_station():

    for _ in range(15):

        xbmc.executebuiltin(
            "SetFocus(50)"
        )

        xbmc.sleep(150)

        label = xbmc.getInfoLabel(
            "ListItem.Label"
        ).strip()

        if not label:
            continue

        if label in ("..", "..."):
            xbmc.executebuiltin(
                "Control.Move(50,1)"
            )

        return








def show_list():
    """
    Senderliste bewusst öffnen.

    Der Wechsel zurück zum Player passiert
    über den Playback-Callback im Metadata-Service.
    """

    HOME.setProperty(
        "RNSE.Radio.ListRequested",
        "true",
    )

    HOME.setProperty(
        "RNSE.Radio.OpenPlayerPending",
        "true",
    )

    xbmc.executebuiltin(
        "Action(Back)"
    )



def show_player():
    """
    Manueller Rückfall-Shortcut im Senderlisten-Header.
    """

    if radio_active():

        clear_list_state()

        xbmc.executebuiltin(
            f"ActivateWindow({RADIO_WINDOW})"
        )

    else:

        xbmcgui.Dialog().notification(
            "Radio",
            "Noch kein Sender aktiv",
            xbmcgui.NOTIFICATION_INFO,
            1800,
        )


def open_if_active():

    xbmc.sleep(300)

    manual_list = (
        HOME.getProperty(
            LIST_REQUEST_PROPERTY
        ).strip().lower()
        == "true"
    )


    if manual_list:


        focus_first_real_station()

        return


    if radio_active():

        xbmc.executebuiltin(
            f"ActivateWindow({RADIO_WINDOW})"
        )

        return


    # erster Start:
    # Liste zeigen und bereits auf die erste Senderwahl warten.

    focus_first_real_station()


def handle_back():
    """
    In den beiden Vollbild-Playern:
        Back -> direkt Hauptmenü

    In Listen / Unterseiten:
        normales Kodi-Back
    """

    radio_player_active = (
        HOME.getProperty(
            "RNSE.Radio.PlayerActive"
        ).strip().lower()
        == "true"
    )

    music_player_active = (
        HOME.getProperty(
            "RNSE.Music.PlayerActive"
        ).strip().lower()
        == "true"
    )


    if radio_player_active or music_player_active:

        # Radio-Auto-Open sicher neutralisieren,
        # damit nichts wieder zurückschubst.
        HOME.clearProperty(
            "RNSE.Radio.OpenPlayerPending"
        )

        HOME.clearProperty(
            "RNSE.Radio.ListRequested"
        )

        HOME.clearProperty(
            "RNSE.Radio.ListWatch"
        )

        clear_list_state()

        xbmc.executebuiltin(
            "ActivateWindow(Home)"
        )

        return


    # Außerhalb der Player:
    # normale Kodi-Hierarchie.
    xbmc.executebuiltin(
        "Action(Back)"
    )



def main():

    action = (
        sys.argv[1].strip().lower()
        if len(sys.argv) > 1
        else ""
    )

    if action == "open-if-active":
        open_if_active()

    elif action == "show-list":
        show_list()

    elif action == "show-player":
        show_player()

    elif action == "back":
        handle_back()


if __name__ == "__main__":
    main()
