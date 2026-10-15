#!/usr/bin/env python3

import fcntl
import os
import re
import subprocess
import time

import xbmc
import xbmcgui


WINDOW = xbmcgui.Window(10000)

PREFIX = "RNSE.Phone."

LOCKFILE = "/tmp/rnse_phone_status.lock"

# Ein kurzer oFono-Aussetzer soll die Anzeige nicht sofort
# auf "Kein Telefon" schalten.
OFFLINE_MISSES_BEFORE_CLEAR = 4

# Hauptzyklus in Sekunden
UPDATE_INTERVAL = 3


def log(message):
    xbmc.log(
        "[RNSE Phone] " + str(message),
        level=xbmc.LOGINFO,
    )


def set_prop(name, value):
    WINDOW.setProperty(
        PREFIX + name,
        str(value),
    )


def clear_phone():
    set_prop("Connected", "false")
    set_prop("Name", "")
    set_prop("Operator", "")
    set_prop("Status", "")
    set_prop("Strength", "0")
    set_prop("Battery", "0")

    for i in range(1, 6):
        set_prop(f"Signal{i}", "false")
        set_prop(f"Battery{i}", "false")


def run_busctl(*args):
    try:
        result = subprocess.run(
            [
                "busctl",
                "--system",
                "call",
                *args,
            ],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )

        if result.returncode != 0:
            return ""

        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        log(
            "busctl timeout: "
            + " ".join(args)
        )
        return ""

    except Exception as exc:
        log(
            "busctl error: "
            + str(exc)
        )
        return ""


def get_string(data, name):
    match = re.search(
        rf'"{re.escape(name)}"\s+s\s+"([^"]*)"',
        data,
    )

    if match:
        return match.group(1)

    return ""


def get_byte(data, name):
    match = re.search(
        rf'"{re.escape(name)}"\s+y\s+(\d+)',
        data,
    )

    if not match:
        return 0

    try:
        return int(match.group(1))

    except ValueError:
        return 0


def friendly_operator(name):
    if not name:
        return ""

    cleaned = name.strip()
    lower = cleaned.lower()

    mappings = {
        "vodafone.de": "Vodafone",
        "telekom.de": "Telekom",
        "telekom": "Telekom",
        "o2 - de": "o2",
        "o2-de": "o2",
        "o2.de": "o2",
    }

    if lower in mappings:
        return mappings[lower]

    if lower.endswith(".de"):
        cleaned = cleaned[:-3]

    return cleaned


def get_active_phone():
    output = run_busctl(
        "org.ofono",
        "/",
        "org.ofono.Manager",
        "GetModems",
    )

    if not output:
        return None, ""

    paths = [
        path
        for path in re.findall(
            r'"([^"]+)"',
            output,
        )
        if path.startswith("/hfp/")
    ]

    for path in paths:
        props = run_busctl(
            "org.ofono",
            path,
            "org.ofono.Modem",
            "GetProperties",
        )

        if not props:
            continue

        online = (
            '"Online" b true'
            in props
        )

        powered = (
            '"Powered" b true'
            in props
        )

        handsfree = (
            '"org.ofono.Handsfree"'
            in props
        )

        network = (
            '"org.ofono.NetworkRegistration"'
            in props
        )

        if not (
            online
            and powered
            and handsfree
            and network
        ):
            continue

        name = get_string(
            props,
            "Name",
        )

        return path, name

    return None, ""


def update_bars(strength, battery):
    # Mobilfunk 0..100 -> 0..5 Balken
    if strength <= 0:
        signal_level = 0

    elif strength < 20:
        signal_level = 1

    elif strength < 40:
        signal_level = 2

    elif strength < 60:
        signal_level = 3

    elif strength < 80:
        signal_level = 4

    else:
        signal_level = 5

    for i in range(1, 6):
        set_prop(
            f"Signal{i}",
            "true"
            if signal_level >= i
            else "false",
        )

    # HFP liefert bei unserem Stack 0..5
    battery = max(
        0,
        min(5, battery),
    )

    for i in range(1, 6):
        set_prop(
            f"Battery{i}",
            "true"
            if battery >= i
            else "false",
        )


def update_phone():
    path, phone_name = get_active_phone()

    if not path:
        return False

    network = run_busctl(
        "org.ofono",
        path,
        "org.ofono.NetworkRegistration",
        "GetProperties",
    )

    handsfree = run_busctl(
        "org.ofono",
        path,
        "org.ofono.Handsfree",
        "GetProperties",
    )

    if not network or not handsfree:
        return False

    status = get_string(
        network,
        "Status",
    )

    operator = friendly_operator(
        get_string(
            network,
            "Name",
        )
    )

    strength = get_byte(
        network,
        "Strength",
    )

    battery = get_byte(
        handsfree,
        "BatteryChargeLevel",
    )

    set_prop(
        "Connected",
        "true",
    )

    set_prop(
        "Name",
        phone_name,
    )

    set_prop(
        "Operator",
        operator,
    )

    set_prop(
        "Status",
        status,
    )

    set_prop(
        "Strength",
        strength,
    )

    set_prop(
        "Battery",
        battery,
    )

    update_bars(
        strength,
        battery,
    )

    return True


def acquire_lock(monitor):
    lock = open(
        LOCKFILE,
        "w",
        encoding="utf-8",
    )

    #
    # Wichtig:
    #
    # Bei einem normalen ReloadSkin läuft die alte Instanz
    # möglicherweise noch. Dann wartet die neue Instanz kurz,
    # statt sofort zu verschwinden.
    #
    deadline = time.monotonic() + 10.0

    while not monitor.abortRequested():
        try:
            fcntl.flock(
                lock,
                fcntl.LOCK_EX
                | fcntl.LOCK_NB,
            )

            lock.seek(0)
            lock.truncate()

            lock.write(
                str(os.getpid())
            )

            lock.flush()

            return lock

        except BlockingIOError:
            if time.monotonic() >= deadline:
                log(
                    "Andere Phone-Status-Instanz "
                    "läuft bereits."
                )

                lock.close()
                return None

            if monitor.waitForAbort(0.5):
                break

    lock.close()
    return None


def main():
    monitor = xbmc.Monitor()

    lock = acquire_lock(
        monitor
    )

    if lock is None:
        return

    misses = 0

    log(
        "Phone-Status-Dienst gestartet."
    )

    try:
        while not monitor.abortRequested():
            success = update_phone()

            if success:
                misses = 0

            else:
                misses += 1

                log(
                    "Telefon nicht erkannt "
                    f"({misses}/"
                    f"{OFFLINE_MISSES_BEFORE_CLEAR})"
                )

                if (
                    misses
                    >= OFFLINE_MISSES_BEFORE_CLEAR
                ):
                    clear_phone()

            if monitor.waitForAbort(
                UPDATE_INTERVAL
            ):
                break

    finally:
        #
        # Absichtlich KEIN clear_phone().
        #
        # Wenn Kodi eine alte Script-Instanz beendet,
        # darf diese nicht mehr die Properties einer
        # bereits gestarteten neuen Instanz löschen.
        #
        try:
            fcntl.flock(
                lock,
                fcntl.LOCK_UN,
            )

            lock.close()

        except Exception:
            pass

        log(
            "Phone-Status-Dienst beendet."
        )


if __name__ == "__main__":
    main()
