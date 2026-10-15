#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import re
import xbmc
import xbmcgui

from PIL import ImageFont


HOME = xbmcgui.Window(10000)
MONITOR = xbmc.Monitor()

PROP = "RNSE.Music.ScrollActive"

FONT_FILE = (
    "/home/pi/.kodi/addons/"
    "skin.estuary.custom/fonts/"
    "NotoSans-Regular.ttf"
)

CONTROL_WIDTH = 940

SCROLL_SPEED = 38.0


# ------------------------------------------------------------
# Timing
# ------------------------------------------------------------

# Neuer Song:
# erstmal schön ruhig am Anfang anzeigen.
INITIAL_WAIT = 6.0

# Kodi braucht nach dem Umschalten von statischem Label
# auf Fadelabel einen Moment, bevor die Bewegung beginnt.
SCROLL_START_DELAY = 2.2

# Wenn das Ende erreicht wurde, noch ganz kurz stehen lassen.
# NICHT mehr mehrere Sekunden.
END_HOLD = 1.0

# Zwischen Titel / Interpret / Album
BETWEEN_FIELDS = 1.5

# Wenn alle nötigen Zeilen einmal dran waren:
FINAL_REST = 8.0

POLL = 0.10


# ------------------------------------------------------------
# Aktuelle Fonts
# ------------------------------------------------------------

FIELDS = {
    "title": {
        "property": "Title",
        "font_size": 75,
    },
    "artist": {
        "property": "Artist",
        "font_size": 60,
    },
    "album": {
        "property": "Album",
        "font_size": 55,
    },
}


FONTS = {
    field: ImageFont.truetype(
        FONT_FILE,
        data["font_size"]
    )
    for field, data in FIELDS.items()
}


def get(name):

    return HOME.getProperty(
        "RNSE.Music." + name
    ).strip()


def connected():

    return (
        HOME.getProperty(
            "RNSE.Music.Connected"
        ).lower()
        == "true"
    )


def fingerprint():

    return (
        get("Title"),
        get("Artist"),
        get("Album"),
    )


def set_active(field=""):

    HOME.setProperty(
        PROP,
        field
    )


def text_width(field, text):

    if not text:
        return 0.0

    font = FONTS[field]

    try:
        return float(
            font.getlength(text)
        )

    except AttributeError:

        box = font.getbbox(text)

        return float(
            box[2] - box[0]
        )


def needs_scroll(field, text):

    return (
        text_width(field, text)
        > CONTROL_WIDTH
    )


def scroll_time(field, text):

    width = text_width(
        field,
        text
    )

    overflow = max(
        0.0,
        width - CONTROL_WIDTH
    )

    # Kodi muss nur den tatsächlich außerhalb des
    # 940-px-Fensters liegenden Bereich bewegen.
    travel = (
        overflow
        / SCROLL_SPEED
    )

    total = (
        SCROLL_START_DELAY
        + travel
        + END_HOLD
    )

    # Kleine Sicherheitsuntergrenze.
    return max(
        3.5,
        total
    )


def wait(seconds, reference):

    end = (
        time.monotonic()
        + seconds
    )

    while time.monotonic() < end:

        if MONITOR.abortRequested():
            return False

        if not connected():
            return False

        if fingerprint() != reference:
            return False

        time.sleep(POLL)

    return True


def current_text(field):

    return get(
        FIELDS[field]["property"]
    )


def main():

    set_active("")

    while not MONITOR.abortRequested():

        if not connected():

            set_active("")

            time.sleep(0.5)
            continue


        current = fingerprint()

        # ====================================================
        # Neuer Zyklus:
        # erstmal alles ruhig am Anfang.
        # ====================================================

        set_active("")

        if not wait(
            INITIAL_WAIT,
            current
        ):
            continue


        restart = False
        something_scrolled = False


        # ====================================================
        # Titel -> Interpret -> Album
        #
        # Nur tatsächlich zu lange Texte bekommen überhaupt
        # einen Scroll-Slot.
        # ====================================================

        for field in [
            "title",
            "artist",
            "album",
        ]:

            text = current_text(field)


            if not needs_scroll(
                field,
                text
            ):
                continue


            something_scrolled = True


            duration = scroll_time(
                field,
                text
            )


            xbmc.log(
                "[RNSE Music Scroll] "
                f"{field}: "
                f"text_width={text_width(field, text):.1f}px "
                f"control={CONTROL_WIDTH}px "
                f"slot={duration:.2f}s",
                xbmc.LOGINFO
            )


            # ------------------------------------------------
            # Genau diese EINE Zeile freigeben.
            # ------------------------------------------------

            set_active(
                field
            )


            if not wait(
                duration,
                current
            ):

                restart = True
                break


            # ------------------------------------------------
            # Sofort wieder statische Anfangsdarstellung.
            # ------------------------------------------------

            set_active("")


            if not wait(
                BETWEEN_FIELDS,
                current
            ):

                restart = True
                break


        if restart:

            set_active("")
            continue


        # ====================================================
        # Nach dem Durchgang längere Ruhe.
        # ====================================================

        set_active("")


        if something_scrolled:

            if not wait(
                FINAL_REST,
                current
            ):
                continue

        else:

            # Kein Text zu lang:
            # einfach ruhig bleiben.
            if not wait(
                2.0,
                current
            ):
                continue


    set_active("")


if __name__ == "__main__":
    main()
