#!/usr/bin/env bash

set -u

SCRIPT_DIR="/home/pi/scripts"
PYTHON="/home/pi/.venv-canbus/bin/python3"
CAN_SCRIPT="$SCRIPT_DIR/read_from_canbus.py"
TX_BRIDGE="$SCRIPT_DIR/can_wifi_bridge_tx.py"
INPUT_BRIDGE="$SCRIPT_DIR/can_input_bridge.py"

CAN_PID=""
TX_PID=""
INPUT_PID=""
CLEANUP_DONE=0
PRODUCTIVE_WAS_RUNNING=0
PRODUCTIVE_LOG="$SCRIPT_DIR/read_from_canbus_manual.log"


cleanup() {
    if [ "$CLEANUP_DONE" -eq 1 ]; then
        return
    fi

    CLEANUP_DONE=1
    trap - EXIT INT TERM

    echo
    echo "========================================"
    echo " MacBook Debug Session wird beendet"
    echo "========================================"
    echo

    if [ -n "$CAN_PID" ] && kill -0 "$CAN_PID" 2>/dev/null; then
        echo "read_from_canbus.py wird beendet ..."
        kill -TERM "$CAN_PID" 2>/dev/null || true

        for _ in 1 2 3 4 5; do
            if ! kill -0 "$CAN_PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done

        if kill -0 "$CAN_PID" 2>/dev/null; then
            echo "WARNUNG: read_from_canbus.py reagiert nicht auf TERM."
            kill -KILL "$CAN_PID" 2>/dev/null || true
        fi

        wait "$CAN_PID" 2>/dev/null || true
    fi

    if [ -n "$INPUT_PID" ] && kill -0 "$INPUT_PID" 2>/dev/null; then
        echo "CAN-Input-Bridge wird beendet ..."
        kill -TERM "$INPUT_PID" 2>/dev/null || true

        for _ in 1 2 3; do
            if ! kill -0 "$INPUT_PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done

        if kill -0 "$INPUT_PID" 2>/dev/null; then
            echo "WARNUNG: CAN-Input-Bridge reagiert nicht auf TERM."
            kill -KILL "$INPUT_PID" 2>/dev/null || true
        fi

        wait "$INPUT_PID" 2>/dev/null || true
    fi

    if [ -n "$TX_PID" ] && kill -0 "$TX_PID" 2>/dev/null; then
        echo "WiFi-TX-Bridge wird beendet ..."
        kill -TERM "$TX_PID" 2>/dev/null || true

        for _ in 1 2 3; do
            if ! kill -0 "$TX_PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done

        if kill -0 "$TX_PID" 2>/dev/null; then
            kill -KILL "$TX_PID" 2>/dev/null || true
        fi

        wait "$TX_PID" 2>/dev/null || true
    fi

    echo
    echo "Debug-Prozesse wurden beendet."
    echo "features.conf wurde nicht verändert."

    echo
    echo "Persistentes CAN-Interface:"
    grep '^can_interface' "$SCRIPT_DIR/features.conf" || true

    echo
    echo "Produktives read_from_canbus.py wird auf can0 gestartet ..."

    if pgrep -f "^$PYTHON $CAN_SCRIPT$" >/dev/null 2>&1; then
        echo "Produktivinstanz läuft bereits."
    else
        cd "$SCRIPT_DIR" || true

        nohup "$PYTHON" "$CAN_SCRIPT"             >> "$PRODUCTIVE_LOG" 2>&1 < /dev/null &

        PRODUCTIVE_PID=$!

        sleep 2

        if kill -0 "$PRODUCTIVE_PID" 2>/dev/null; then
            echo "OK: Produktivinstanz läuft als PID $PRODUCTIVE_PID."
        else
            echo "WARNUNG: Produktivinstanz konnte nicht gestartet werden."
            echo "Log: $PRODUCTIVE_LOG"
        fi
    fi

    echo
    echo "Das Fahrzeug-Setup ist wieder aktiv."
}


handle_signal() {
    echo
    echo "Stop-Signal empfangen."
    cleanup
    exit 0
}


trap cleanup EXIT
trap handle_signal INT TERM


echo "========================================"
echo " Audi Automotive - MacBook Debug Session"
echo "========================================"
echo

for file in "$CAN_SCRIPT" "$TX_BRIDGE" "$INPUT_BRIDGE"; do
    if [ ! -f "$file" ]; then
        echo "FEHLER: $file wurde nicht gefunden."
        exit 1
    fi
done

if [ ! -x "$PYTHON" ]; then
    echo "FEHLER: Python-VENV wurde nicht gefunden:"
    echo "$PYTHON"
    exit 1
fi


echo "===== Produktivinstanz prüfen ====="

PRODUCTIVE_PIDS="$(pgrep -f "^$PYTHON $CAN_SCRIPT$" || true)"

if [ -n "$PRODUCTIVE_PIDS" ]; then
    PRODUCTIVE_WAS_RUNNING=1

    echo "Produktives read_from_canbus.py läuft:"
    echo "$PRODUCTIVE_PIDS"
    echo "Wird für die Debug-Session beendet ..."

    for pid in $PRODUCTIVE_PIDS; do
        kill -TERM "$pid" 2>/dev/null || true
    done

    for _ in 1 2 3 4 5; do
        if ! pgrep -f "^$PYTHON $CAN_SCRIPT$" >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done

    REMAINING="$(pgrep -f "^$PYTHON $CAN_SCRIPT$" || true)"

    if [ -n "$REMAINING" ]; then
        echo "WARNUNG: Produktivinstanz reagiert nicht auf TERM."

        for pid in $REMAINING; do
            kill -KILL "$pid" 2>/dev/null || true
        done
    fi

    echo "OK: Produktivinstanz pausiert."
else
    echo "Keine Produktivinstanz aktiv."
fi

echo

echo "[1/4] vcan0 vorbereiten ..."

if ! ip link show vcan0 >/dev/null 2>&1; then
    echo "      vcan0 existiert nicht - wird angelegt."
    sudo ip link add dev vcan0 type vcan || exit 1
fi

sudo ip link set vcan0 up || exit 1

echo "      OK: vcan0 ist verfügbar."
echo


echo "[2/4] CAN-Input-Bridge can0 -> vcan0 starten ..."

cd "$SCRIPT_DIR" || exit 1

"$PYTHON" "$INPUT_BRIDGE" &
INPUT_PID=$!

sleep 1

if ! kill -0 "$INPUT_PID" 2>/dev/null; then
    echo "FEHLER: CAN-Input-Bridge konnte nicht gestartet werden."
    exit 1
fi

echo "      OK: Input-Bridge läuft als PID $INPUT_PID."
echo "      Weiterleitung: can0 / 0x461 -> vcan0"
echo


echo "[3/4] WiFi-TX-Bridge starten ..."

cd "$SCRIPT_DIR" || exit 1

"$PYTHON" "$TX_BRIDGE" &
TX_PID=$!

sleep 1

if ! kill -0 "$TX_PID" 2>/dev/null; then
    echo "FEHLER: WiFi-TX-Bridge konnte nicht gestartet werden."
    exit 1
fi

echo "      OK: TX-Bridge läuft als PID $TX_PID."
echo


echo "[4/4] read_from_canbus.py mit Runtime-Override starten ..."

AUTOMOTIVE_CAN_INTERFACE=vcan0 \
"$PYTHON" "$CAN_SCRIPT" &
CAN_PID=$!

sleep 1

if ! kill -0 "$CAN_PID" 2>/dev/null; then
    echo "FEHLER: read_from_canbus.py konnte nicht gestartet werden."
    exit 1
fi


echo
echo "----------------------------------------"
echo " DEBUG-MODUS AKTIV"
echo
echo " Runtime CAN       : vcan0"
echo " Persistente Config: bleibt unverändert"
echo
echo " read_from_canbus PID : $CAN_PID"
echo " Input-Bridge PID     : $INPUT_PID"
echo " TX-Bridge PID        : $TX_PID"
echo
echo " CTRL+C beendet die komplette Debug-Session."
echo "----------------------------------------"
echo


wait "$CAN_PID"
EXIT_CODE=$?

echo
echo "read_from_canbus.py wurde mit Code $EXIT_CODE beendet."

exit "$EXIT_CODE"
