#!/usr/bin/env python3

import json
import os
import subprocess
import time
from pathlib import Path


# ------------------------------------------------------------
# Konfiguration
# ------------------------------------------------------------

MODE = os.environ.get(
    "CAN_HEALTH_MODE",
    "AUTO"
).upper()

CONFIG_PATH = Path("/home/pi/config.json")

STATUS_DIR = Path("/run/rpi-automotive")
STATUS_FILE = STATUS_DIR / "can-health.json"

STATE_DIR = Path("/var/lib/rpi-automotive")

# Persistenter Schutz gegen Reboot-Schleifen:
REBOOT_MARKER = STATE_DIR / "can-auto-reboot-attempted"

CHECK_INTERVAL = 2

# Nach dieser Zeit ohne RX wird die Anzeige gelb.
TRAFFIC_TIMEOUT = 15

# Erst deutlich später versuchen wir eine Soft-Recovery.
NO_TRAFFIC_RECOVERY_TIME = 35

# Anzahl aufeinanderfolgender harter Fehler,
# bevor eine Recovery ausgelöst wird.
HARD_FAILURE_THRESHOLD = 3

# Nach mehreren erfolglosen harten Recoveries
# darf im echten CAN-Modus einmal rebootet werden.
MAX_HARD_RECOVERIES_BEFORE_REBOOT = 3


# ------------------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------------------

def log(message):
    print(
        time.strftime("%Y-%m-%d %H:%M:%S"),
        message,
        flush=True
    )


def run(command):
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False
        )
    except Exception as exc:
        log(f"Command error {command}: {exc}")
        return None


def systemctl(*args):
    return run([
        "/usr/bin/systemctl",
        *args
    ])


def service_active(name):
    result = systemctl(
        "is-active",
        "--quiet",
        name
    )

    return bool(
        result and result.returncode == 0
    )


def service_enabled(name):
    result = systemctl(
        "is-enabled",
        "--quiet",
        name
    )

    return bool(
        result and result.returncode == 0
    )


def restart_service(name):
    log(f"Restarting {name}")

    systemctl(
        "restart",
        name
    )


def configured_interface():
    try:
        with CONFIG_PATH.open(
            "r",
            encoding="utf-8"
        ) as handle:

            data = json.load(handle)

        interface = data.get(
            "can_interface"
        )

        if interface in (
            "can0",
            "vcan0"
        ):
            return interface

    except Exception as exc:
        log(
            f"Could not read "
            f"{CONFIG_PATH}: {exc}"
        )

    return None


def interface_exists(interface):
    return Path(
        f"/sys/class/net/{interface}"
    ).exists()


def interface_up(interface):
    flags_file = Path(
        f"/sys/class/net/{interface}/flags"
    )

    try:
        flags = int(
            flags_file.read_text().strip(),
            16
        )

        # Linux IFF_UP
        return bool(
            flags & 0x1
        )

    except Exception:
        return False


def rx_packets(interface):
    path = Path(
        f"/sys/class/net/"
        f"{interface}/statistics/rx_packets"
    )

    try:
        return int(
            path.read_text().strip()
        )

    except Exception:
        return None


def can_bus_off(interface):
    if interface != "can0":
        return False

    result = run([
        "/sbin/ip",
        "-details",
        "link",
        "show",
        interface
    ])

    if not result:
        return False

    return (
        "BUS-OFF"
        in result.stdout.upper()
    )


def choose_interface():
    """
    AUTO:
      1. Berücksichtigt die gleiche config.json
         wie can_handler.py.
      2. Falls config can0 sagt, can0 aber nicht
         verfügbar ist und vcan0 UP ist, nehmen
         wir vcan0 als Bench-Fallback.
    """

    if MODE == "CAR":
        return "can0"

    if MODE == "BENCH":
        return "vcan0"

    configured = configured_interface()

    if configured == "vcan0":
        return "vcan0"

    if configured == "can0":
        if interface_up("can0"):
            return "can0"

        if interface_up("vcan0"):
            return "vcan0"

        return "can0"

    if interface_up("can0"):
        return "can0"

    if interface_up("vcan0"):
        return "vcan0"

    if interface_exists("can0"):
        return "can0"

    if interface_exists("vcan0"):
        return "vcan0"

    return "can0"


def optional_service_problem(name):
    """
    Ein optionaler Dienst zählt nur als Fehler,
    wenn er auf diesem Pi überhaupt aktiviert ist.
    """

    if not service_enabled(name):
        return False

    return not service_active(name)


def write_status(data):
    STATUS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary = STATUS_FILE.with_suffix(
        ".tmp"
    )

    temporary.write_text(
        json.dumps(
            data,
            indent=2
        ),
        encoding="utf-8"
    )

    temporary.replace(
        STATUS_FILE
    )


# ------------------------------------------------------------
# Recovery
# ------------------------------------------------------------

def restart_core_services():
    """
    Reihenfolge bewusst:
    zentraler Handler zuerst,
    danach die Verbraucher.
    """

    restart_service(
        "can_handler.service"
    )

    time.sleep(1)

    if service_enabled(
        "can_base_function.service"
    ):
        restart_service(
            "can_base_function.service"
        )

    restart_service(
        "can_keyboard_control.service"
    )


def recover_interface(interface):
    if interface == "vcan0":

        log(
            "Bench recovery: "
            "restarting vcan0 only."
        )

        restart_service(
            "vcan0.service"
        )

        time.sleep(1)

        restart_core_services()

        return

    log(
        "Vehicle recovery: "
        "restarting can0."
    )

    restart_service(
        "can0-setup.service"
    )

    time.sleep(1)

    restart_core_services()


def hard_recovery(interface):
    log(
        f"Hard recovery for {interface}"
    )

    # Erst Interface reparieren,
    # danach die komplette Core-Kette.
    recover_interface(
        interface
    )


def maybe_reboot(interface):
    """
    vcan0 darf NIEMALS einen Fahrzeug-/Pi-Reboot
    verursachen.

    Reboot-Marker bleibt auch über einen Reboot
    erhalten. Erst ein später wirklich gesunder
    CAN-Zustand entfernt ihn wieder.
    """

    if interface != "can0":
        return False

    STATE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if REBOOT_MARKER.exists():

        log(
            "Automatic reboot already attempted. "
            "Reboot blocked to prevent a loop."
        )

        return False

    REBOOT_MARKER.write_text(
        str(time.time()),
        encoding="utf-8"
    )

    log(
        "CAN recovery failed repeatedly. "
        "Performing ONE protected automatic reboot."
    )

    systemctl(
        "reboot"
    )

    return True


# ------------------------------------------------------------
# Hauptprogramm
# ------------------------------------------------------------

def main():

    log(
        f"CAN Health Monitor starting "
        f"in mode {MODE}"
    )

    last_interface = None
    last_rx = None
    last_rx_time = time.monotonic()

    hard_failure_count = 0
    hard_recovery_count = 0

    no_traffic_recovery_stage = 0

    recovery_active = False

    while True:

        interface = choose_interface()

        bench = (
            interface == "vcan0"
        )

        # Interface-Wechsel:
        if interface != last_interface:

            log(
                f"Active CAN interface: "
                f"{interface}"
            )

            last_interface = interface
            last_rx = None
            last_rx_time = time.monotonic()

            hard_failure_count = 0
            hard_recovery_count = 0
            no_traffic_recovery_stage = 0

        exists = interface_exists(
            interface
        )

        up = interface_up(
            interface
        )

        bus_off = can_bus_off(
            interface
        )

        handler_ok = service_active(
            "can_handler.service"
        )

        keyboard_ok = service_active(
            "can_keyboard_control.service"
        )

        base_ok = not optional_service_problem(
            "can_base_function.service"
        )

        uinput_ok = Path(
            "/dev/uinput"
        ).exists()

        current_rx = rx_packets(
            interface
        )

        # ----------------------------------------
        # RX-Aktivität erkennen
        # ----------------------------------------

        if current_rx is not None:

            if last_rx is None:
                last_rx = current_rx

            elif current_rx > last_rx:

                last_rx = current_rx
                last_rx_time = time.monotonic()

                no_traffic_recovery_stage = 0

            else:
                last_rx = current_rx

        traffic_age = (
            time.monotonic()
            - last_rx_time
        )

        traffic_ok = (
            traffic_age
            <= TRAFFIC_TIMEOUT
        )

        # ----------------------------------------
        # Harte Fehler
        # ----------------------------------------

        problems = []

        if not exists:
            problems.append(
                f"{interface} missing"
            )

        elif not up:
            problems.append(
                f"{interface} down"
            )

        if bus_off:
            problems.append(
                "CAN BUS-OFF"
            )

        if not handler_ok:
            problems.append(
                "can_handler inactive"
            )

        if not keyboard_ok:
            problems.append(
                "keyboard handler inactive"
            )

        if not base_ok:
            problems.append(
                "can_base_function inactive"
            )

        if not uinput_ok:
            problems.append(
                "/dev/uinput missing"
            )

        hard_fault = bool(
            problems
        )

        # ----------------------------------------
        # Status bestimmen
        # ----------------------------------------

        if hard_fault:

            status = "red"
            hard_failure_count += 1

        else:

            hard_failure_count = 0
            hard_recovery_count = 0
            recovery_active = False

            if traffic_ok:
                status = "green"

                # Ein wirklich gesunder CAN-Bus
                # hebt den Reboot-Schutz wieder auf.
                if (
                    interface == "can0"
                    and REBOOT_MARKER.exists()
                ):
                    try:
                        REBOOT_MARKER.unlink()
                    except Exception:
                        pass

            else:
                status = "yellow"

        # ----------------------------------------
        # Health-Datei schreiben
        # ----------------------------------------

        health = {
            "status": status,
            "mode": MODE,
            "interface": interface,
            "bench": bench,

            "interface_exists": exists,
            "interface_up": up,
            "bus_off": bus_off,

            "handler": handler_ok,
            "keyboard": keyboard_ok,
            "base_function": base_ok,
            "uinput": uinput_ok,

            "rx_packets": current_rx,
            "traffic_age_seconds": round(
                traffic_age,
                1
            ),
            "traffic": traffic_ok,

            "recovery": recovery_active,
            "problems": problems,

            "timestamp": time.time()
        }

        write_status(
            health
        )

        # ----------------------------------------
        # HARD RECOVERY
        # ----------------------------------------

        if (
            hard_fault
            and hard_failure_count
                >= HARD_FAILURE_THRESHOLD
        ):

            recovery_active = True

            hard_recovery_count += 1
            hard_failure_count = 0

            log(
                "Hard CAN fault: "
                + ", ".join(problems)
            )

            hard_recovery(
                interface
            )

            # Nur echter Fahrzeug-CAN darf
            # als letzte Eskalationsstufe rebooten.
            if (
                interface == "can0"
                and hard_recovery_count
                    >= MAX_HARD_RECOVERIES_BEFORE_REBOOT
            ):

                if maybe_reboot(
                    interface
                ):
                    return

        # ----------------------------------------
        # SOFT RECOVERY BEI KEINEM RX
        # ----------------------------------------

        elif (
            not hard_fault
            and not traffic_ok
            and traffic_age
                >= NO_TRAFFIC_RECOVERY_TIME
        ):

            # vCAN:
            # Kein Hardware-Reset nur weil gerade
            # niemand Testframes sendet.
            if bench:

                pass

            # echter CAN:
            elif no_traffic_recovery_stage == 0:

                log(
                    "No CAN RX for a longer time. "
                    "Soft-restarting handler chain."
                )

                restart_core_services()

                no_traffic_recovery_stage = 1
                last_rx_time = time.monotonic()

            elif no_traffic_recovery_stage == 1:

                log(
                    "Still no CAN RX. "
                    "Reinitializing can0 once."
                )

                recover_interface(
                    "can0"
                )

                no_traffic_recovery_stage = 2
                last_rx_time = time.monotonic()

            # Stage 2:
            # Kein Reboot nur wegen fehlendem Traffic.
            # Das Fahrzeug könnte schlicht schlafen.

        time.sleep(
            CHECK_INTERVAL
        )


if __name__ == "__main__":
    main()
