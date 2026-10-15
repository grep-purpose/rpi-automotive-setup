#!/usr/bin/env python3
"""Mira Screenshot V1.2 - persistente Telegram-Warteschlange."""

import fcntl
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HOME = Path("/home/pi")
IMAGES = HOME / "Pictures/Mira"
STATE = HOME / ".local/state/mira"
CONFIG = HOME / ".config/mira/screenshots.json"
DATABASE = STATE / "screenshot_queue.sqlite3"
SENDER = Path("/usr/local/lib/mira/mira_telegram_send.py")


def prepare():
    STATE.mkdir(parents=True, exist_ok=True)
    STATE.chmod(0o700)


def connect():
    prepare()
    db = sqlite3.connect(DATABASE, timeout=15)
    db.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            path TEXT PRIMARY KEY,
            created INTEGER NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            next_attempt INTEGER NOT NULL DEFAULT 0
        )
    """)
    db.commit()
    DATABASE.chmod(0o600)
    return db


def automatic_enabled():
    if not CONFIG.exists():
        return False
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    return data.get("automatic_upload") is True


def setting(value):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.parent.chmod(0o700)

    temp = CONFIG.with_suffix(".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"automatic_upload": value}, f)
    temp.replace(CONFIG)
    CONFIG.chmod(0o600)

    print("Automatischer Upload:", "EIN" if value else "AUS")


def enqueue(filename):
    image = Path(filename).resolve()
    folder = IMAGES.resolve()

    if image.parent != folder or image.suffix.lower() != ".png":
        raise ValueError("Nur Mira-PNG-Dateien erlaubt")

    if not image.is_file() or image.stat().st_size == 0:
        raise ValueError("Screenshot fehlt oder ist leer")

    with connect() as db:
        db.execute(
            """INSERT OR IGNORE INTO uploads
               (path, created) VALUES (?, ?)""",
            (str(image), int(time.time()))
        )
    print("Mira: Telegram-Upload vorgemerkt.")


def process():
    prepare()

    # Verhindert zwei gleichzeitig laufende Versandprozesse.
    lock_path = STATE / "upload.lock"
    with open(lock_path, "a+") as lock:
        lock_path.chmod(0o600)

        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Mira: Upload-Dienst läuft bereits.")
            return

        with connect() as db:
            rows = db.execute(
                """SELECT path, attempts FROM uploads
                   WHERE next_attempt <= ?
                   ORDER BY created ASC LIMIT 20""",
                (int(time.time()),)
            ).fetchall()

            for filename, attempts in rows:
                image = Path(filename)

                # Fehlende Bilder nicht stillschweigend vergessen.
                if not image.is_file():
                    print("Mira: Vorgemerkte Aufnahme fehlt.")
                    db.execute(
                        "UPDATE uploads SET next_attempt=? WHERE path=?",
                        (int(time.time()) + 3600, filename)
                    )
                    db.commit()
                    continue

                try:
                    result = subprocess.run(
                        [sys.executable, str(SENDER), filename],
                        capture_output=True,
                        text=True,
                        timeout=45,
                        check=False
                    )

                    if result.returncode == 0:
                        db.execute(
                            "DELETE FROM uploads WHERE path=?",
                            (filename,)
                        )
                        db.commit()
                        print("Mira: Screenshot übertragen.")
                    else:
                        raise RuntimeError("Telegram-Versand fehlgeschlagen")

                except Exception:
                    # Exponentielle Wartezeit, maximal eine Stunde.
                    delay = min(3600, 60 * (2 ** min(attempts, 6)))
                    db.execute(
                        """UPDATE uploads
                           SET attempts=attempts+1,
                               next_attempt=?
                           WHERE path=?""",
                        (int(time.time()) + delay, filename)
                    )
                    db.commit()
                    print("Mira: Upload wird später erneut versucht.")


def status():
    print("Automatischer Upload:",
          "EIN" if automatic_enabled() else "AUS")

    with connect() as db:
        count = db.execute("SELECT COUNT(*) FROM uploads").fetchone()[0]
        print("Ausstehende Uploads:", count)


if __name__ == "__main__":
    try:
        command = sys.argv[1] if len(sys.argv) > 1 else ""

        if command == "enqueue" and len(sys.argv) == 3:
            enqueue(sys.argv[2])
        elif command == "process" and len(sys.argv) == 2:
            process()
        elif command == "enabled" and len(sys.argv) == 2:
            sys.exit(0 if automatic_enabled() else 1)
        elif command == "status" and len(sys.argv) == 2:
            status()
        elif command == "auto-on" and len(sys.argv) == 2:
            setting(True)
        elif command == "auto-off" and len(sys.argv) == 2:
            setting(False)
        else:
            raise ValueError("Unbekannter Warteschlangen-Befehl")

    except Exception as error:
        print("Mira Queue Fehler:", type(error).__name__,
              file=sys.stderr)
        sys.exit(1)
