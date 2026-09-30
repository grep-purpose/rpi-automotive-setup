#!/usr/bin/env python3

import json
import subprocess
import time
from pathlib import Path

CHECK_INTERVAL = 10
BOOT_GRACE = 20

STAGE1_WAIT = 5
STAGE2_WAIT = 8

FAILED_RECOVERIES_BEFORE_REBOOT = 3
REBOOT_COOLDOWN = 30 * 60

STATUS_DIR = Path("/run/rpi-automotive")
STATUS_FILE = STATUS_DIR / "input-watchdog.json"

STATE_DIR = Path("/var/lib/rpi-automotive")
REBOOT_MARKER = STATE_DIR / "input-watchdog-last-reboot"


def log(message):
    print(
        time.strftime("%Y-%m-%d %H:%M:%S"),
        message,
        flush=True
    )


def run(command):
    return subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    ).returncode == 0


def service_active(name):
    return run([
        "systemctl",
        "is-active",
        "--quiet",
        name
    ])


def virtual_keyboard_exists():
    try:
        text = Path(
            "/proc/bus/input/devices"
        ).read_text(errors="ignore")

        return 'N: Name="can-virtual-keyboard"' in text
    except Exception:
        return False


def input_health():
    handler = service_active(
        "can_handler.service"
    )

    keyboard_service = service_active(
        "can_keyboard_control.service"
    )

    keyboard_device = virtual_keyboard_exists()

    healthy = (
        handler
        and keyboard_service
        and keyboard_device
    )

    return {
        "healthy": healthy,
        "handler": handler,
        "keyboard_service": keyboard_service,
        "keyboard_device": keyboard_device,
    }


def write_status(data):
    STATUS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    tmp = STATUS_FILE.with_suffix(".tmp")

    tmp.write_text(
        json.dumps(
            data,
            indent=2
        )
    )

    tmp.replace(STATUS_FILE)


def restart_keyboard():
    log(
        "Recovery Stufe 1: "
        "can_keyboard_control wird neu gestartet."
    )

    run([
        "systemctl",
        "restart",
        "can_keyboard_control.service"
    ])


def restart_input_stack():
    log(
        "Recovery Stufe 2: "
        "CAN Handler + Keyboard werden neu gestartet."
    )

    run([
        "systemctl",
        "restart",
        "can_handler.service"
    ])

    time.sleep(2)

    run([
        "systemctl",
        "restart",
        "can_keyboard_control.service"
    ])


def reboot_allowed():
    STATE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not REBOOT_MARKER.exists():
        return True

    try:
        last = float(
            REBOOT_MARKER.read_text().strip()
        )
    except Exception:
        return True

    return (
        time.time() - last
        >= REBOOT_COOLDOWN
    )


def emergency_reboot():
    if not reboot_allowed():
        log(
            "Reboot wäre nötig, ist aber durch "
            "die 30-Minuten-Sperre blockiert."
        )
        return False

    STATE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    REBOOT_MARKER.write_text(
        str(time.time())
    )

    log(
        "Recovery Stufe 3: "
        "Input weiterhin defekt. "
        "Kontrollierter Reboot."
    )

    subprocess.Popen([
        "systemctl",
        "reboot"
    ])

    return True


def wait_and_check(seconds):
    time.sleep(seconds)
    return input_health()


def main():
    log("Input Watchdog gestartet.")

    log(
        f"Boot-Schonzeit: "
        f"{BOOT_GRACE} Sekunden."
    )

    time.sleep(BOOT_GRACE)

    failed_recoveries = 0

    while True:
        health = input_health()

        write_status({
            **health,
            "failed_recoveries": failed_recoveries,
            "timestamp": time.time(),
        })

        if health["healthy"]:
            failed_recoveries = 0
            time.sleep(CHECK_INTERVAL)
            continue

        log(
            "Input nicht gesund: "
            f"handler={health['handler']} "
            f"keyboard_service={health['keyboard_service']} "
            f"keyboard_device={health['keyboard_device']}"
        )

        # -------------------------
        # Recovery Stufe 1
        # -------------------------

        restart_keyboard()

        health = wait_and_check(
            STAGE1_WAIT
        )

        if health["healthy"]:
            log(
                "Recovery Stufe 1 erfolgreich."
            )

            failed_recoveries = 0
            continue

        # -------------------------
        # Recovery Stufe 2
        # -------------------------

        restart_input_stack()

        health = wait_and_check(
            STAGE2_WAIT
        )

        if health["healthy"]:
            log(
                "Recovery Stufe 2 erfolgreich."
            )

            failed_recoveries = 0
            continue

        failed_recoveries += 1

        log(
            "Recovery fehlgeschlagen. "
            f"Versuch {failed_recoveries}/"
            f"{FAILED_RECOVERIES_BEFORE_REBOOT}"
        )

        write_status({
            **health,
            "failed_recoveries": failed_recoveries,
            "timestamp": time.time(),
        })

        # -------------------------
        # Recovery Stufe 3
        # -------------------------

        if (
            failed_recoveries
            >= FAILED_RECOVERIES_BEFORE_REBOOT
        ):
            if emergency_reboot():
                return

            # Reboot gesperrt:
            # nicht alle 10 Sekunden erneut versuchen
            failed_recoveries = 0

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
