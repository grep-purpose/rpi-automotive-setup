#!/usr/bin/env bash

set -u

SCRIPT_DIR="/home/pi/scripts"
FEATURES="$SCRIPT_DIR/features.conf"
PYTHON="/home/pi/.venv-canbus/bin/python3"
CAN_SCRIPT="$SCRIPT_DIR/read_from_canbus.py"

BACKUP="$(mktemp /tmp/features.conf.macbook-debug.XXXXXX)"

restore_config() {
    echo
    echo "========================================"
    echo " MacBook Debug Session wird beendet"
    echo "========================================"

    if [ -f "$BACKUP" ]; then
        cp -a "$BACKUP" "$FEATURES"
        rm -f "$BACKUP"

        echo "OK: Originale features.conf wiederhergestellt."
    else
        echo "WARNUNG: Temporäre Sicherung nicht gefunden."
    fi

    echo
    echo "Aktives CAN-Interface:"
    grep '^can_interface' "$FEATURES" || true

    echo
    echo "Das Fahrzeug-Setup ist wieder aktiv."
}

trap restore_config EXIT INT TERM

echo "========================================"
echo " Audi Automotive - MacBook Debug Session"
echo "========================================"
echo

if [ ! -f "$FEATURES" ]; then
    echo "FEHLER: $FEATURES wurde nicht gefunden."
    exit 1
fi

if [ ! -f "$CAN_SCRIPT" ]; then
    echo "FEHLER: $CAN_SCRIPT wurde nicht gefunden."
    exit 1
fi

if [ ! -x "$PYTHON" ]; then
    echo "FEHLER: Python-VENV wurde nicht gefunden:"
    echo "$PYTHON"
    exit 1
fi

echo "[1/4] Originale features.conf sichern ..."
cp -a "$FEATURES" "$BACKUP"

echo "      Sicherung: $BACKUP"
echo

echo "[2/4] vcan0 prüfen ..."

if ! ip link show vcan0 >/dev/null 2>&1; then
    echo "      vcan0 existiert nicht - wird angelegt."
    sudo ip link add dev vcan0 type vcan || exit 1
fi

sudo ip link set vcan0 up || exit 1

echo "      OK: vcan0 ist verfügbar."
echo

echo "[3/4] Debug-Konfiguration aktivieren ..."

python3 - "$FEATURES" <<'PY'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

new_text, count = re.subn(
    r"(?m)^(\s*can_interface\s*=\s*).*$",
    r"\1'vcan0'",
    text,
    count=1,
)

if count != 1:
    raise SystemExit(
        "FEHLER: can_interface wurde in features.conf nicht eindeutig gefunden."
    )

path.write_text(new_text, encoding="utf-8")
PY

echo
grep '^can_interface' "$FEATURES"
echo

echo "[4/4] read_from_canbus.py starten ..."
echo
echo "----------------------------------------"
echo " DEBUG-MODUS AKTIV"
echo " Raspberry Pi -> vcan0"
echo " CTRL+C beendet die Debug-Session."
echo " Danach wird can0 automatisch restauriert."
echo "----------------------------------------"
echo

cd "$SCRIPT_DIR" || exit 1

"$PYTHON" "$CAN_SCRIPT"

EXIT_CODE=$?

echo
echo "read_from_canbus.py wurde mit Code $EXIT_CODE beendet."

exit "$EXIT_CODE"
