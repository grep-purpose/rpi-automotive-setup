#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Einfacher, konservativer HUDIY-Manövericon-Decoder.

Version 1:
- links
- rechts
- links halten
- rechts halten
- unbekannt

Wichtig:
Bei Unsicherheit wird absichtlich "" zurückgegeben.
"""

import hashlib
import io
from typing import Dict

from PIL import Image


_icon_cache: Dict[str, str] = {}


def _load_mask(icon_bytes: bytes):
    """
    PNG laden und in eine einfache Schwarz/Weiss-Maske umwandeln.
    Liefert eine Liste von Zeilen mit True/False.
    """
    image = Image.open(io.BytesIO(icon_bytes)).convert("RGBA")

    # Einheitliche kleine Größe -> Analyse wird sehr schnell.
    image.thumbnail((128, 128))

    width, height = image.size
    pixels = image.load()

    mask = []

    for y in range(height):
        row = []

        for x in range(width):
            r, g, b, a = pixels[x, y]

            # Transparenz ignorieren.
            # Helle Pixel gelten als Navi-Symbol.
            brightness = (int(r) + int(g) + int(b)) / 3.0
            active = a > 40 and brightness > 100

            row.append(active)

        mask.append(row)

    return mask, width, height


def _count_region(mask, x1, y1, x2, y2):
    total = 0

    for y in range(y1, y2):
        for x in range(x1, x2):
            if mask[y][x]:
                total += 1

    return total


def classify_nav_icon(icon_bytes: bytes) -> str:
    """
    Analysiert ein HUDIY-Manöver-PNG.

    Rückgabe:
        "links"
        "rechts"
        "links halten"
        "rechts halten"
        ""

    "" bedeutet: nicht sicher genug.
    """

    if not icon_bytes:
        return ""

    digest = hashlib.sha256(icon_bytes).hexdigest()

    cached = _icon_cache.get(digest)
    if cached is not None:
        return cached

    try:
        mask, width, height = _load_mask(icon_bytes)
    except Exception:
        _icon_cache[digest] = ""
        return ""

    if width < 20 or height < 20:
        _icon_cache[digest] = ""
        return ""

    #
    # Wir interessieren uns hauptsächlich für den oberen Bereich.
    #
    # Der untere Bereich ist bei Navigationsicons meistens nur der
    # gemeinsame "Stamm". Oben erkennt man, wohin der Weg weitergeht.
    #
    top_end = int(height * 0.60)
    middle = width // 2

    left = _count_region(
        mask,
        0,
        0,
        middle,
        top_end
    )

    right = _count_region(
        mask,
        middle,
        0,
        width,
        top_end
    )

    total = left + right

    if total < 20:
        _icon_cache[digest] = ""
        return ""

    left_ratio = left / total
    right_ratio = right / total

    #
    # Keine deutliche Seitendominanz:
    # könnte geradeaus, Kreisverkehr, U-Turn usw. sein.
    #
    dominance = abs(right_ratio - left_ratio)

    if dominance < 0.16:
        result = ""
        _icon_cache[digest] = result
        return result

    if right_ratio > left_ratio:
        dominant = right
        secondary = left
        side = "rechts"
    else:
        dominant = left
        secondary = right
        side = "links"

    #
    # Wenn auf BEIDEN Seiten im oberen Bildbereich deutlich Symbolfläche
    # vorhanden ist, deutet das eher auf eine Gabelung / "halten" hin.
    #
    # Beispiel unseres A5-Icons:
    #
    #        ↗
    #       /
    #   \  /
    #    \/
    #
    # Der linke Ast bleibt sichtbar, während der aktive Weg rechts führt.
    #
    secondary_ratio = (
        secondary / dominant
        if dominant > 0
        else 0.0
    )

    if secondary_ratio >= 0.20:
        result = f"{side} halten"
    else:
        result = side

    _icon_cache[digest] = result
    return result


def icon_debug_info(icon_bytes: bytes) -> dict:
    """Zusatzwerte fürs Logging/Testen."""
    if not icon_bytes:
        return {
            "sha256": "",
            "result": "",
        }

    digest = hashlib.sha256(icon_bytes).hexdigest()

    try:
        mask, width, height = _load_mask(icon_bytes)

        top_end = int(height * 0.60)
        middle = width // 2

        left = _count_region(mask, 0, 0, middle, top_end)
        right = _count_region(mask, middle, 0, width, top_end)

        total = left + right

        return {
            "sha256": digest,
            "width": width,
            "height": height,
            "left": left,
            "right": right,
            "left_ratio": round(left / total, 3) if total else 0,
            "right_ratio": round(right / total, 3) if total else 0,
            "result": classify_nav_icon(icon_bytes),
        }

    except Exception as exc:
        return {
            "sha256": digest,
            "result": "",
            "error": repr(exc),
        }
