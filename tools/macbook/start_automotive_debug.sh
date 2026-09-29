#!/usr/bin/env bash

set -u

# ------------------------------------------------------------
# Audi Automotive - MacBook One-Click Debug
# ------------------------------------------------------------

REPO="/home/seb/rpi-automotive-setup"
PYTHON="/home/seb/.venv-canbus/bin/python3"

GUI="$REPO/tools/macbook/debugging_script.py"
RX_BRIDGE="$REPO/tools/macbook/bridge/can_wifi_bridge_rx.py"

PI_HOST="192.168.0.59"
PI_USER="pi"
PI_KEY="/home/seb/.ssh/rpi_automotive"
PI_LAUNCHER="/home/pi/scripts/start_macbook_debug.sh"

GUI_PID=""
RX_PID=""
SSH_PID=""
CLEANUP_DONE=0


cleanup() {
    if [ "$CLEANUP_DONE" -eq 1 ]; then
        return
    fi

    CLEANUP_DONE=1
    trap - EXIT INT TERM

    echo
    echo "========================================"
    echo " Audi Automotive Debug wird beendet"
    echo "========================================"
    echo

    # --------------------------------------------------------
    # Raspberry Pi sauber stoppen.
    # Der Pi-Launcher besitzt einen getesteten SIGTERM-Cleanup.
    # --------------------------------------------------------
    echo "[1/3] Raspberry-Pi-Debugsession stoppen ..."

    ssh \
        -i "$PI_KEY" \
        -o IdentitiesOnly=yes \
        -o BatchMode=yes \
        -o ConnectTimeout=5 \
        "$PI_USER@$PI_HOST" \
        '
        PID="$(pgrep -f "^bash /home/pi/scripts/start_macbook_debug.sh$" | head -1)"

        if [ -z "$PID" ]; then
            PID="$(pgrep -f "start_macbook_debug.sh" | head -1)"
        fi

        if [ -n "$PID" ]; then
            echo "      Pi-Launcher PID: $PID"
            kill -TERM "$PID"
        else
            echo "      Kein Pi-Debug-Launcher aktiv."
        fi
        ' 2>/dev/null || \
        echo "      WARNUNG: Pi konnte beim Cleanup nicht erreicht werden."

    # Dem Pi-Cleanup kurz Zeit geben.
    sleep 4

    # Lokalen SSH-Client beenden, falls er noch wartet.
    if [ -n "$SSH_PID" ] && kill -0 "$SSH_PID" 2>/dev/null; then
        kill -TERM "$SSH_PID" 2>/dev/null || true
        wait "$SSH_PID" 2>/dev/null || true
    fi

    echo
    echo "[2/3] MacBook RX-Bridge stoppen ..."

    if [ -n "$RX_PID" ] && kill -0 "$RX_PID" 2>/dev/null; then
        kill -TERM "$RX_PID" 2>/dev/null || true

        for _ in 1 2 3; do
            if ! kill -0 "$RX_PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done

        if kill -0 "$RX_PID" 2>/dev/null; then
            kill -KILL "$RX_PID" 2>/dev/null || true
        fi

        wait "$RX_PID" 2>/dev/null || true
    fi

    echo
    echo "[3/3] Debug-GUI stoppen ..."

    if [ -n "$GUI_PID" ] && kill -0 "$GUI_PID" 2>/dev/null; then
        kill -TERM "$GUI_PID" 2>/dev/null || true

        for _ in 1 2 3; do
            if ! kill -0 "$GUI_PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done

        if kill -0 "$GUI_PID" 2>/dev/null; then
            kill -KILL "$GUI_PID" 2>/dev/null || true
        fi

        wait "$GUI_PID" 2>/dev/null || true
    fi

    echo
    echo "========================================"
    echo " Debug-Session beendet"
    echo "========================================"
}


handle_signal() {
    cleanup
    exit 0
}


trap cleanup EXIT
trap handle_signal INT TERM


echo "========================================"
echo " Audi Automotive - One-Click Debug"
echo "========================================"
echo


# ------------------------------------------------------------
# Voraussetzungen prüfen
# ------------------------------------------------------------

for file in "$GUI" "$RX_BRIDGE" "$PI_KEY"; do
    if [ ! -f "$file" ]; then
        echo "FEHLER: Datei fehlt:"
        echo "$file"
        exit 1
    fi
done

if [ ! -x "$PYTHON" ]; then
    echo "FEHLER: Python-VENV fehlt:"
    echo "$PYTHON"
    exit 1
fi


# ------------------------------------------------------------
# vcan0
# ------------------------------------------------------------

echo "[1/5] MacBook vcan0 prüfen ..."

if ! ip link show vcan0 >/dev/null 2>&1; then
    echo "      vcan0 fehlt."
    echo
    echo "Bitte einmal manuell anlegen:"
    echo "sudo ip link add dev vcan0 type vcan"
    echo "sudo ip link set vcan0 up"
    exit 1
fi

if ! ip link show vcan0 | grep -q 'UP'; then
    echo "      vcan0 ist vorhanden, aber nicht UP."
    echo "      Bitte ausführen: sudo ip link set vcan0 up"
    exit 1
fi

echo "      OK: vcan0 ist verfügbar."


# ------------------------------------------------------------
# Prüfen, ob alte Instanzen laufen
# ------------------------------------------------------------

echo
echo "[2/5] Alte Debug-Prozesse prüfen ..."

if pgrep -f "$RX_BRIDGE" >/dev/null 2>&1; then
    echo "FEHLER: Eine RX-Bridge läuft bereits."
    exit 1
fi

if pgrep -f "$GUI" >/dev/null 2>&1; then
    echo "FEHLER: Die Debug-GUI läuft bereits."
    exit 1
fi

echo "      OK: Keine alten MacBook-Debugprozesse."


# ------------------------------------------------------------
# RX-Bridge
# ------------------------------------------------------------

echo
echo "[3/5] WiFi RX-Bridge starten ..."

cd "$REPO" || exit 1

"$PYTHON" "$RX_BRIDGE" &
RX_PID=$!

sleep 1

if ! kill -0 "$RX_PID" 2>/dev/null; then
    echo "FEHLER: RX-Bridge konnte nicht gestartet werden."
    exit 1
fi

echo "      OK: RX-Bridge PID $RX_PID."


# ------------------------------------------------------------
# Raspberry Pi
# ------------------------------------------------------------

echo
echo "[4/5] Raspberry-Pi-Debugsession starten ..."

ssh \
    -i "$PI_KEY" \
    -o IdentitiesOnly=yes \
    -o BatchMode=yes \
    -o ServerAliveInterval=5 \
    -o ServerAliveCountMax=3 \
    "$PI_USER@$PI_HOST" \
    "cd /home/pi/scripts && exec ./start_macbook_debug.sh" &

SSH_PID=$!

sleep 3

if ! kill -0 "$SSH_PID" 2>/dev/null; then
    echo "FEHLER: SSH/Pi-Debugsession wurde unerwartet beendet."
    exit 1
fi

echo "      OK: SSH/Pi-Debugsession läuft."


# ------------------------------------------------------------
# GUI
# ------------------------------------------------------------

echo
echo "[5/5] Virtuelles FIS / RNS-E starten ..."

cd "$REPO/tools/macbook" || exit 1

"$PYTHON" "$GUI" &
GUI_PID=$!

sleep 2

if ! kill -0 "$GUI_PID" 2>/dev/null; then
    echo "FEHLER: Debug-GUI konnte nicht gestartet werden."
    exit 1
fi


echo
echo "========================================"
echo " DEBUG-SYSTEM AKTIV"
echo "========================================"
echo
echo "MacBook:"
echo "  RX-Bridge : PID $RX_PID"
echo "  GUI       : PID $GUI_PID"
echo
echo "Raspberry Pi:"
echo "  SSH       : PID $SSH_PID"
echo "  Runtime CAN: vcan0"
echo
echo "Persistente Pi-Konfiguration bleibt can0."
echo
echo "Dieses Terminal geöffnet lassen."
echo "Beenden später mit CTRL+C."
echo "========================================"
echo


# GUI ist der natürliche Lebenszyklus der lokalen Session.
# Wird das Fenster geschlossen, räumt der EXIT-Trap alles auf.
wait "$GUI_PID"
GUI_EXIT=$?

echo
echo "Debug-GUI wurde mit Code $GUI_EXIT beendet."

exit "$GUI_EXIT"
