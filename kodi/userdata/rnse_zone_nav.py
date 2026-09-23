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
# Footer  = 9100
# Kein Header
# ----------------------------------------------------------

if xbmc.getCondVisibility("Window.IsActive(Home)"):

    if direction == "down":
        if focused(9000):
            focus(9100)

    elif direction == "up":
        if focused(9100):
            focus(9000)

    sys.exit(0)


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
content = [50, 51]
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
