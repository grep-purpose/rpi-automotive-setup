#!/usr/bin/env python3

import json
import os
import subprocess
import time
from pathlib import Path

STATUS_DIR = Path("/run/rpi-automotive")
STATUS_FILE = STATUS_DIR / "can-health.json"
CONFIG_FILE = Path("/home/pi/config.json")

CHECK_INTERVAL = 2.0
TRAFFIC_TIMEOUT = 15.0


def interface_exists(name):
    return Path(f"/sys/class/net/{name}").exists()


def interface_up(name):
    try:
        state = Path(f"/sys/class/net/{name}/operstate").read_text().strip()
        return state in ("up", "unknown")
    except Exception:
        return False


def rx_packets(name):
    try:
        return int(
            Path(f"/sys/class/net/{name}/statistics/rx_packets")
            .read_text()
            .strip()
        )
    except Exception:
        return 0


def bus_off(name):
    try:
        result = subprocess.run(
            ["ip", "-details", "link", "show", name],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return "BUS-OFF" in result.stdout
    except Exception:
        return False


def service_active(name):
    try:
        return (
            subprocess.run(
                ["systemctl", "is-active", "--quiet", name],
                timeout=2,
            ).returncode
            == 0
        )
    except Exception:
        return False


def configured_interface():
    try:
        cfg = json.loads(CONFIG_FILE.read_text())
        interface = cfg.get("can_interface")

        if interface in ("can0", "vcan0"):
            return interface
    except Exception:
        pass

    if interface_exists("can0") and interface_up("can0"):
        return "can0"

    if interface_exists("vcan0") and interface_up("vcan0"):
        return "vcan0"

    return "can0"


def atomic_write(data):
    STATUS_DIR.mkdir(parents=True, exist_ok=True)

    temp = STATUS_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2))
    os.replace(temp, STATUS_FILE)


def main():
    last_rx = {}
    last_traffic = {}

    while True:
        interface = configured_interface()

        exists = interface_exists(interface)
        up = exists and interface_up(interface)

        current_rx = rx_packets(interface) if exists else 0
        previous_rx = last_rx.get(interface)

        now = time.monotonic()

        if previous_rx is None:
            last_traffic.setdefault(interface, now)

        elif current_rx != previous_rx:
            last_traffic[interface] = now

        last_rx[interface] = current_rx

        traffic_age = now - last_traffic.get(interface, now)
        traffic = traffic_age <= TRAFFIC_TIMEOUT

        handler = service_active("can_handler.service")
        keyboard = service_active("can_keyboard_control.service")
        is_bus_off = bus_off(interface) if interface == "can0" else False

        problems = []

        if not exists:
            problems.append("interface_missing")

        if exists and not up:
            problems.append("interface_down")

        if is_bus_off:
            problems.append("bus_off")

        if not handler:
            problems.append("can_handler")

        if not keyboard:
            problems.append("can_keyboard")

        if problems:
            status = "red"

        elif not traffic:
            status = "yellow"

        else:
            status = "green"

        atomic_write(
            {
                "status": status,
                "interface": interface,
                "interface_exists": exists,
                "interface_up": up,
                "bus_off": is_bus_off,
                "handler": handler,
                "keyboard": keyboard,
                "rx_packets": current_rx,
                "traffic": traffic,
                "traffic_age_seconds": round(traffic_age, 1),
                "problems": problems,
                "timestamp": time.time(),
            }
        )

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
