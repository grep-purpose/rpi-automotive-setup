#!/usr/bin/env python3

import json
import sys
import uuid
import urllib.request
import urllib.error
from pathlib import Path

CONFIG = Path("/home/pi/.config/mira/telegram.json")


def send_document(filename):
    image = Path(filename)

    if not image.is_file() or image.suffix.lower() != ".png":
        raise ValueError("PNG-Datei fehlt oder ist ungültig")

    if not CONFIG.is_file():
        raise ValueError("Telegram-Konfiguration fehlt")

    settings = json.loads(CONFIG.read_text(encoding="utf-8"))

    token = settings["bot_token"]
    chat_id = str(settings["chat_id"])

    boundary = uuid.uuid4().hex

    def field(name, value):
        return (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode("utf-8")

    body = (
        field("chat_id", chat_id)
        + field("caption", "Mira Automotive | Screenshot")
        + (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="document"; '
            f'filename="{image.name}"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode("utf-8")
        + image.read_bytes()
        + f"\r\n--{boundary}--\r\n".encode("utf-8")
    )

    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendDocument",
        data=body,
        headers={
            "Content-Type":
                f"multipart/form-data; boundary={boundary}"
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)

    if not result.get("ok"):
        raise RuntimeError("Telegram hat den Versand abgelehnt")


def main():
    if len(sys.argv) != 2:
        print("Verwendung: mira_telegram_send.py DATEI")
        return 2

    try:
        send_document(sys.argv[1])
        print("Mira: Telegram-Upload erfolgreich!")
        return 0

    except urllib.error.HTTPError as error:
        print(
            f"Mira: Telegram HTTP-Fehler {error.code}",
            file=sys.stderr,
        )
    except Exception as error:
        # Keine geheimen Tokens in Fehlermeldungen ausgeben
        print(
            f"Mira: Telegram-Versand fehlgeschlagen "
            f"({type(error).__name__})",
            file=sys.stderr,
        )

    return 1


if __name__ == "__main__":
    sys.exit(main())
