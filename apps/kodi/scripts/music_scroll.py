#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import xbmc
import xbmcgui


HOME = xbmcgui.Window(10000)
MONITOR = xbmc.Monitor()

POLL = 0.10

INITIAL_PAUSE = 3.0

PAGE_TIME = {
    "title": 2.8,
    "artist": 2.8,
    "album": 2.8,
}

REST_TIME = {
    "title": 8.0,
    "artist": 10.0,
    "album": 12.0,
}


# ------------------------------------------------------------
# Visuelle Breite der aktuellen 940-px-Felder
#
# bewusst etwas konservativ:
# lieber früher auf zwei Seiten als abgeschnittener Text.
# ------------------------------------------------------------

PAGE_LIMIT = {
    "title": 20.5,
    "artist": 30.0,
    "album": 32.0,
}


SOURCE_PROPS = {
    "title": "RNSE.Music.Title",
    "artist": "RNSE.Music.Artist",
    "album": "RNSE.Music.Album",
}

DISPLAY_PROPS = {
    "title": "RNSE.Music.DisplayTitle",
    "artist": "RNSE.Music.DisplayArtist",
    "album": "RNSE.Music.DisplayAlbum",
}


def prop(name):
    return HOME.getProperty(name).strip()


def set_prop(name, value):
    HOME.setProperty(
        name,
        value or ""
    )


def connected():
    return (
        prop("RNSE.Music.Connected").lower()
        == "true"
    )


def source_values():

    return {
        field: prop(source_prop)
        for field, source_prop
        in SOURCE_PROPS.items()
    }


def fingerprint():

    values = source_values()

    return (
        values["title"],
        values["artist"],
        values["album"],
    )


def visual_char_width(ch):

    if ch in "WwMm@%&":
        return 1.55

    if ch in "ABCDEFGHKNOPQRSTUVXYZ":
        return 1.18

    if ch in "mw":
        return 1.35

    if ch in "ilIjtfr.,:;'!|":
        return 0.55

    if ch == " ":
        return 0.55

    if ch.isdigit():
        return 0.95

    return 1.0


def visual_length(text):

    return sum(
        visual_char_width(ch)
        for ch in text
    )


def split_word(word, limit):
    """
    Notfall für absurd lange Einzelwörter ohne Leerzeichen.
    """

    pages = []
    current = ""

    for ch in word:

        trial = current + ch

        if (
            current
            and visual_length(trial) > limit
        ):
            pages.append(current)
            current = ch
        else:
            current = trial

    if current:
        pages.append(current)

    return pages


def paginate(text, limit):

    text = " ".join(
        text.split()
    ).strip()

    if not text:
        return [""]

    if visual_length(text) <= limit:
        return [text]


    words = text.split(" ")

    pages = []
    current = ""


    for word in words:

        # sehr langes Einzelwort
        if visual_length(word) > limit:

            if current:
                pages.append(current)
                current = ""

            pieces = split_word(
                word,
                limit
            )

            pages.extend(
                pieces[:-1]
            )

            current = pieces[-1]
            continue


        trial = (
            word
            if not current
            else current + " " + word
        )


        if visual_length(trial) <= limit:

            current = trial

        else:

            if current:
                pages.append(current)

            current = word


    if current:
        pages.append(current)


    return pages or [text]


def all_pages(values):

    return {
        field: paginate(
            values[field],
            PAGE_LIMIT[field]
        )
        for field in [
            "title",
            "artist",
            "album",
        ]
    }


def show_first_pages(pages):

    for field in [
        "title",
        "artist",
        "album",
    ]:

        value = (
            pages[field][0]
            if pages[field]
            else ""
        )

        set_prop(
            DISPLAY_PROPS[field],
            value
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


def main():

    last_fp = None


    while not MONITOR.abortRequested():

        if not connected():

            for display_prop in DISPLAY_PROPS.values():
                set_prop(
                    display_prop,
                    ""
                )

            last_fp = None
            time.sleep(0.5)
            continue


        values = source_values()
        fp = fingerprint()

        pages = all_pages(
            values
        )


        # Bei Songwechsel sofort Seite 1 anzeigen.
        if fp != last_fp:

            show_first_pages(
                pages
            )

            last_fp = fp


        # Keine einzige Zeile benötigt Paging.
        if all(
            len(pages[field]) == 1
            for field in pages
        ):

            show_first_pages(
                pages
            )

            time.sleep(0.5)
            continue


        # Erst alles ruhig stehen lassen.
        show_first_pages(
            pages
        )

        if not wait(
            INITIAL_PAUSE,
            fp
        ):
            continue


        restart = False


        # ====================================================
        # Immer nur eine Zeile zur selben Zeit.
        # Titel -> Interpret -> Album
        # ====================================================

        for field in [
            "title",
            "artist",
            "album",
        ]:

            field_pages = pages[field]


            # passt vollständig -> nichts tun
            if len(field_pages) <= 1:
                continue


            # Seite 2, 3, ...
            for page in field_pages[1:]:

                set_prop(
                    DISPLAY_PROPS[field],
                    page
                )

                if not wait(
                    PAGE_TIME[field],
                    fp
                ):
                    restart = True
                    break


            if restart:
                break


            # Zurück auf Seite 1
            set_prop(
                DISPLAY_PROPS[field],
                field_pages[0]
            )


            # Danach Ruhe
            if not wait(
                REST_TIME[field],
                fp
            ):
                restart = True
                break


        if restart:
            continue


        # kompletter Zyklus fertig:
        # alles wieder Anfangsseiten
        show_first_pages(
            pages
        )


if __name__ == "__main__":
    main()
