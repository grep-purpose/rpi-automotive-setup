import sys
import xbmc

direction = sys.argv[1].lower() if len(sys.argv) > 1 else ""

def focused(cid):
    return xbmc.getCondVisibility(f"Control.HasFocus({cid})")

def visible(cid):
    return xbmc.getCondVisibility(f"Control.IsVisible({cid})")

def focus(cid):
    xbmc.executebuiltin(f"SetFocus({cid})")

def first_visible(ids):
    for cid in ids:
        if visible(cid):
            return cid
    return None


# ----------------------------------------------------------
# HOME
# Content = 9000
# Now Playing = 9201
# Footer = 9100 / 9101
# ----------------------------------------------------------

if xbmc.getCondVisibility("Window.IsActive(Home)"):

    now_playing_visible = visible(9201)

    if direction == "down":
        if focused(9000):
            focus(9201 if now_playing_visible else 9100)
        elif focused(9201):
            focus(9100)

    elif direction == "up":
        if focused(9100) or focused(9101):
            focus(9201 if now_playing_visible else 9000)
        elif focused(9201):
            focus(9000)

    elif direction == "left":
        if focused(9100):
            focus(9101)
        elif focused(9101):
            focus(9100)
        else:
            xbmc.executebuiltin("PlayerControl(Previous)")

    elif direction == "right":
        if focused(9100):
            focus(9101)
        elif focused(9101):
            focus(9100)
        else:
            xbmc.executebuiltin("PlayerControl(Next)")

    sys.exit(0)


# ----------------------------------------------------------
# WETTER
#
# Header:
#   9001 / 9003
#
# Content:
#   50 = STÜNDLICH
#   51 = TÄGLICH
#   52 = RADAR
#
# Footer:
#   9002 / 9004
#
# Steuerkreuz:
#   oben/unten = Zone wechseln
#
# Drehregler:
#   wird NICHT hier behandelt
# ----------------------------------------------------------

if xbmc.getCondVisibility("Window.IsActive(Weather)"):

    header = [9001, 9003]
    footer = [9002, 9004]
    content = [50, 51, 52]

    header_visible = first_visible(header)
    footer_visible = first_visible(footer)

    in_header = any(focused(x) for x in header)
    in_content = any(focused(x) for x in content)
    in_footer = any(focused(x) for x in footer)

    # Aktuell gewählten Wettermodus bestimmen
    if xbmc.getCondVisibility(
        "String.IsEqual(Window(home).Property(WeatherView),daily)"
    ):
        weather_content = 51

    elif xbmc.getCondVisibility(
        "String.IsEqual(Window(home).Property(WeatherView),radar)"
    ):
        weather_content = 52

    else:
        weather_content = 50


    if direction == "up":

        # Footer -> aktuell gewählter Wettermodus
        if in_footer:
            focus(weather_content)

        # Content -> Header
        elif in_content and header_visible:
            focus(header_visible)

        # Unbekannter Fokus -> Content
        elif not in_header and not in_content and not in_footer:
            focus(weather_content)


    elif direction == "down":

        # Header -> aktuell gewählter Wettermodus
        if in_header:
            focus(weather_content)

        # Content -> Footer
        elif in_content and footer_visible:
            focus(footer_visible)

        # Unbekannter Fokus -> Content
        elif not in_header and not in_content and not in_footer:
            focus(weather_content)


    sys.exit(0)



# --- RNSE MUSIC ZONE START ---
#
# Custom-Musikplayer
#
# Header:
#   9001 / 9003
#
# Content:
#   9100 = Previous
#   9101 = Play/Pause
#   9102 = Next
#
# Footer:
#   9002 / 9004
#
# Die Fadenkreuztasten werden global über rnse_zone_nav.py
# behandelt. Der Drehregler bleibt innerhalb der XML über
# onup/ondown auf 9100/9101/9102.
# ----------------------------------------------------------

music_content = [9100, 9101, 9102]

music_active = any(
    visible(cid)
    for cid in music_content
)

if music_active:

    music_header = [9001, 9003]
    music_footer = [9002, 9004]

    music_header_visible = first_visible(
        music_header
    )

    music_footer_visible = first_visible(
        music_footer
    )

    in_music_header = any(
        focused(cid)
        for cid in music_header
    )

    in_music_content = any(
        focused(cid)
        for cid in music_content
    )

    in_music_footer = any(
        focused(cid)
        for cid in music_footer
    )

    if direction == "up":

        # Footer -> Hauptbereich
        if in_music_footer:
            focus(9101)

        # Hauptbereich -> Header
        elif in_music_content:
            if music_header_visible:
                focus(music_header_visible)

        # unbekannter Fokus -> Hauptbereich
        elif not in_music_header:
            focus(9101)

    elif direction == "down":

        # Header -> Hauptbereich
        if in_music_header:
            focus(9101)

        # Hauptbereich -> Footer
        elif in_music_content:
            if music_footer_visible:
                focus(music_footer_visible)

        # unbekannter Fokus -> Hauptbereich
        elif not in_music_footer:
            focus(9101)

    sys.exit(0)

# --- RNSE MUSIC ZONE END ---

# ----------------------------------------------------------
# Standard-MMI-Struktur
#
# Header:
#   9001 / 9003
#
# Content:
#   50 / 51
#
# Footer:
#   9002 / 9004
# ----------------------------------------------------------

header = [9001, 9003]
content = [50, 51, 52]
footer = [9002, 9004]

header_visible = first_visible(header)
content_visible = first_visible(content)
footer_visible = first_visible(footer)

in_header = any(focused(x) for x in header)
in_content = any(focused(x) for x in content)
in_footer = any(focused(x) for x in footer)


if direction == "up":

    # Footer -> Content
    if in_footer and content_visible:
        focus(content_visible)

    # Content -> Header
    elif in_content and header_visible:
        focus(header_visible)

    # Wenn Fokus unbekannt ist -> Content
    elif not in_header and not in_content and not in_footer:
        if content_visible:
            focus(content_visible)


elif direction == "down":

    # Header -> Content
    if in_header and content_visible:
        focus(content_visible)

    # Content -> Footer
    elif in_content and footer_visible:
        focus(footer_visible)

    # Wenn Fokus unbekannt ist -> Content
    elif not in_header and not in_content and not in_footer:
        if content_visible:
            focus(content_visible)
