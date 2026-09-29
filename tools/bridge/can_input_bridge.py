#!/usr/bin/env python3

import signal
import sys

import can


SOURCE_INTERFACE = "can0"
TARGET_INTERFACE = "vcan0"

# RNS-E Bedienung / Dreh-Drücksteller
FORWARDED_IDS = {
    0x461,
}

running = True


def handle_signal(signum, frame):
    global running
    running = False


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


def main():
    source_bus = None
    target_bus = None
    forwarded = 0

    print("========================================")
    print(" Audi Automotive - CAN Input Bridge")
    print("========================================")
    print()
    print(f"Quelle : {SOURCE_INTERFACE}")
    print(f"Ziel   : {TARGET_INTERFACE}")
    print(
        "CAN-IDs: "
        + ", ".join(
            f"0x{can_id:03X}"
            for can_id in sorted(FORWARDED_IDS)
        )
    )
    print()

    try:
        source_bus = can.interface.Bus(
            channel=SOURCE_INTERFACE,
            interface="socketcan",
            can_filters=[
                {
                    "can_id": can_id,
                    "can_mask": 0x7FF,
                    "extended": False,
                }
                for can_id in FORWARDED_IDS
            ],
            receive_own_messages=False,
        )

        target_bus = can.interface.Bus(
            channel=TARGET_INTERFACE,
            interface="socketcan",
            receive_own_messages=False,
        )

        print("Input-Bridge aktiv.")
        print()

        while running:
            message = source_bus.recv(timeout=0.5)

            if message is None:
                continue

            if message.arbitration_id not in FORWARDED_IDS:
                continue

            forwarded_message = can.Message(
                arbitration_id=message.arbitration_id,
                data=message.data,
                is_extended_id=message.is_extended_id,
                is_remote_frame=message.is_remote_frame,
                is_error_frame=False,
            )

            target_bus.send(forwarded_message)
            forwarded += 1

    except Exception as exc:
        print(
            f"FEHLER in CAN Input Bridge: {exc}",
            file=sys.stderr,
        )
        return 1

    finally:
        if source_bus is not None:
            source_bus.shutdown()

        if target_bus is not None:
            target_bus.shutdown()

        print()
        print("Input-Bridge beendet.")
        print(f"Weitergeleitete Frames: {forwarded}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
