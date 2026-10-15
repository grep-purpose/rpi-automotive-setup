#!/usr/bin/env python3
"""Mira USB Manager A1: USB-Erkennung und inkrementeller Musikindex."""

import json
import os
import re
import subprocess
import time
from pathlib import Path

STORE = Path("/home/pi/.kodi/userdata/mira/usb")
EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".wav", ".aac", ".opus", ".wma"}
SKIP = {
    ".rockbox", ".trashes", ".spotlight-v100",
    "$recycle.bin", "system volume information",
    "calendars", "contacts", "notes"
}


def run(*args, timeout=15):
    try:
        return subprocess.run(
            args, capture_output=True, text=True,
            timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    os.replace(temp, path)


def usb_devices():
    result = run(
        "lsblk", "-J", "-o",
        "NAME,PATH,TRAN,TYPE,FSTYPE,LABEL,UUID,MOUNTPOINTS"
    )
    if not result or result.returncode:
        raise RuntimeError("lsblk konnte nicht ausgeführt werden")

    roots = json.loads(result.stdout).get("blockdevices", [])
    found = []

    def inspect(node, is_usb=False):
        is_usb = is_usb or node.get("tran") == "usb"

        if is_usb and node.get("fstype") and node.get("uuid"):
            mounts = [
                p for p in (node.get("mountpoints") or [])
                if isinstance(p, str) and p.startswith("/")
            ]
            if mounts:
                found.append({
                    "device": node.get("path", ""),
                    "uuid": node["uuid"],
                    "label": node.get("label") or "",
                    "fstype": node.get("fstype") or "",
                    "mount": mounts[0],
                })

        for child in node.get("children") or []:
            inspect(child, is_usb)

    for root in roots:
        inspect(root)

    return found


def metadata(path):
    data = {
        "title": path.stem,
        "artist": "Unbekannter Interpret",
        "album": "Unbekanntes Album",
        "track": 0,
    }

    probe = run(
        "ffprobe", "-v", "error",
        "-show_entries",
        "format_tags=title,artist,album,track:"
        "stream_tags=title,artist,album,track",
        "-of", "json", str(path),
        timeout=12
    )

    if not probe or probe.returncode:
        return data

    try:
        parsed = json.loads(probe.stdout)
        tags = {}

        for stream in parsed.get("streams", []):
            tags.update({
                str(k).lower(): v
                for k, v in stream.get("tags", {}).items()
            })

        tags.update({
            str(k).lower(): v
            for k, v in parsed.get("format", {}).get("tags", {}).items()
        })

        for key in ("title", "artist", "album"):
            value = str(tags.get(key) or "").strip()
            if value:
                data[key] = value

        try:
            data["track"] = int(
                str(tags.get("track", "0")).split("/")[0]
            )
        except ValueError:
            pass

    except (ValueError, TypeError):
        pass

    return data


def index_device(device):
    uuid = device["uuid"]
    mount = Path(device["mount"])
    key = re.sub(r"[^A-Za-z0-9_-]", "_", uuid)
    cache_path = STORE / ("library-" + key + ".json")

    if not mount.is_dir() or not os.path.ismount(mount):
        return None

    # Lesebare Dateien erfassen, auch in iPod_Control/Music/F00.
    try:
        old = json.loads(cache_path.read_text(encoding="utf-8"))
        previous = old.get("files", {})
        if old.get("uuid") != uuid:
            previous = {}
    except (OSError, ValueError, TypeError):
        previous = {}

    current = {}
    created = 0
    reused = 0
    checked = 0

    print(
        f"[Mira USB] Scanne {device['label'] or uuid} "
        f"unter {mount}",
        flush=True
    )

    for root, directories, filenames in os.walk(
        mount, followlinks=False
    ):
        directories[:] = [
            d for d in directories
            if d.lower() not in SKIP and not d.startswith(".")
        ]

        for filename in filenames:
            path = Path(root) / filename
            if path.suffix.lower() not in EXTENSIONS:
                continue

            try:
                stat = path.stat()
                if not path.is_file():
                    continue
                relative = str(path.relative_to(mount))
                signature = [stat.st_size, stat.st_mtime_ns]
            except (OSError, ValueError):
                continue

            checked += 1

            if checked == 1 or checked % 10 == 0:
                print(
                    f"[Mira USB] {checked} Musikdateien geprüft, "
                    f"{created} analysiert, "
                    f"{reused} aus Cache",
                    flush=True
                )

            previous_entry = previous.get(relative, {})

            if previous_entry.get("signature") == signature:
                info = previous_entry.get("metadata")
                if isinstance(info, dict):
                    current[relative] = previous_entry
                    reused += 1
                    continue

            current[relative] = {
                "signature": signature,
                "metadata": metadata(path)
            }
            created += 1

    # Beim Abziehen waehrend eines Scans keinen Teilindex speichern.
    if not os.path.ismount(mount):
        print("ABBRUCH: USB-Gerät während des Scans entfernt", flush=True)
        return None

    # Bei Lesefehlern nach dem Abziehen den alten Index erhalten.
    result = {
        "version": 1,
        "uuid": uuid,
        "label": device["label"],
        "fstype": device["fstype"],
        "files": current,
    }

    atomic_json(cache_path, result)

    print(
        f"{device['label'] or uuid}: "
        f"{len(current)} Titel, {created} neu/geändert, "
        f"{reused} wiederverwendet",
        flush=True
    )

    return {
        **device,
        "tracks": len(current),
        "index": str(cache_path),
    }


def main():
    STORE.mkdir(parents=True, exist_ok=True)

    devices = usb_devices()
    active = []

    for device in devices:
        # Ausschliesslich Partitionen eines USB-Gerätes,
        # die bereits wirklich gemountet sind.
        if device["mount"] in ("/", "/boot", "/boot/firmware"):
            continue
        try:
            indexed = index_device(device)
            if indexed:
                active.append(indexed)
        except Exception as exc:
            print(
                "INDEXFEHLER:",
                device["uuid"], repr(exc),
                flush=True
            )

    atomic_json(
        STORE / "devices.json",
        {
            "updated": int(time.time()),
            "devices": active
        }
    )

    if not active:
        print("Keine eingebundenen USB-Musikquellen", flush=True)


if __name__ == "__main__":
    main()
