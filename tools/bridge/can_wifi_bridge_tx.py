#!/home/pi/.venv-canbus/bin/python3

import socket
import struct
import sys
import time

import can


CAN_INTERFACE = "vcan0"
MACBOOK_IP = "192.168.0.142"
UDP_PORT = 29536

# Für den ersten Test übertragen wir ausschließlich die FIS-IDs.
FIS_IDS = {
    0x265,
    0x267,
    0x667,
    0x66B,
}

# Einfaches eigenes Paketformat:
# magic(4) + can_id(4) + dlc(1) + data(0..8)
MAGIC = b"ACAN"


def main():
    print("==============================================")
    print(" Audi CAN WiFi Debug Bridge - TX")
    print("==============================================")
    print(f"Quelle : {CAN_INTERFACE}")
    print(f"Ziel   : {MACBOOK_IP}:{UDP_PORT}")
    print("CAN IDs:", ", ".join(f"0x{x:03X}" for x in sorted(FIS_IDS)))
    print()
    print("WICHTIG: can0 wird NICHT verwendet.")
    print("Beenden mit Ctrl+C.")
    print()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    bus = can.interface.Bus(
        channel=CAN_INTERFACE,
        interface="socketcan",
        receive_own_messages=False,
    )

    sent = 0

    try:
        while True:
            msg = bus.recv(timeout=1.0)

            if msg is None:
                continue

            if msg.is_extended_id:
                continue

            if msg.arbitration_id not in FIS_IDS:
                continue

            data = bytes(msg.data[:8])

            packet = (
                MAGIC
                + struct.pack("!I", msg.arbitration_id)
                + struct.pack("!B", len(data))
                + data
            )

            sock.sendto(packet, (MACBOOK_IP, UDP_PORT))
            sent += 1

            print(
                f"TX #{sent:05d}  "
                f"0x{msg.arbitration_id:03X}  "
                f"{data.hex(' ').upper()}"
            )

    except KeyboardInterrupt:
        print()
        print("Bridge beendet.")

    finally:
        bus.shutdown()
        sock.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FEHLER: {exc!r}", file=sys.stderr)
        sys.exit(1)
