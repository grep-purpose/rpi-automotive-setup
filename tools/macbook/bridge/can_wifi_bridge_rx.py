#!/usr/bin/env python3

import socket
import struct
import sys

import can


UDP_PORT = 29536
CAN_INTERFACE = "vcan0"

ALLOWED_IDS = {
    0x265,
    0x267,
    0x667,
    0x66B,
}

MAGIC = b"ACAN"


def main():
    print("========================================")
    print(" Audi CAN WiFi Bridge - RX")
    print("========================================")
    print(f"UDP-Port : {UDP_PORT}")
    print(f"Ziel-CAN : {CAN_INTERFACE}")
    print("Protokoll: ACAN binary")
    print()
    print("Warte auf CAN-Nachrichten vom Raspberry Pi ...")
    print("Abbruch mit CTRL+C")
    print()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))

    bus = can.interface.Bus(
        channel=CAN_INTERFACE,
        interface="socketcan",
        receive_own_messages=False,
    )

    received = 0

    try:
        while True:
            packet, address = sock.recvfrom(1024)

            # Paket:
            # magic(4) + can_id(4) + dlc(1) + data(0..8)
            if len(packet) < 9:
                print(
                    f"IGNORIERT von {address[0]}: "
                    f"Paket zu kurz ({len(packet)} Bytes)"
                )
                continue

            if packet[:4] != MAGIC:
                print(
                    f"IGNORIERT von {address[0]}: "
                    f"ungültiger Header {packet[:4]!r}"
                )
                continue

            can_id = struct.unpack("!I", packet[4:8])[0]
            dlc = packet[8]

            if can_id not in ALLOWED_IDS:
                continue

            if dlc > 8:
                print(
                    f"IGNORIERT von {address[0]}: "
                    f"ungültige DLC {dlc}"
                )
                continue

            expected_length = 9 + dlc

            if len(packet) != expected_length:
                print(
                    f"IGNORIERT von {address[0]}: "
                    f"Paketlänge {len(packet)}, erwartet {expected_length}"
                )
                continue

            data = packet[9:9 + dlc]

            msg = can.Message(
                arbitration_id=can_id,
                data=data,
                is_extended_id=False,
            )

            bus.send(msg)
            received += 1

            print(
                f"RX #{received:05d}  "
                f"{address[0]}  "
                f"0x{can_id:03X}  "
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
