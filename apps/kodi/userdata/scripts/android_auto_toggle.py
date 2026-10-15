#!/usr/bin/env python3

import socket

HOST = "127.0.0.1"
PORT = 23456

try:
    with socket.create_connection((HOST, PORT), timeout=2) as sock:
        sock.sendall(b"android_auto\n")
except Exception as e:
    print("Android-Auto-Umschaltung fehlgeschlagen:", e)
