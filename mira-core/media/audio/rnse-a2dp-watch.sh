#!/bin/bash

PHONE_MAC="F4:2B:8C:23:CD:78"
DEVICE_PATH="dev_F4_2B_8C_23_CD_78"

LOG="/var/log/rnse-a2dp-watch.log"
MAX_SIZE=2097152

LAST_STATE=""

rotate_log() {
    if [ -f "$LOG" ]; then
        SIZE="$(stat -c%s "$LOG" 2>/dev/null || echo 0)"

        if [ "$SIZE" -ge "$MAX_SIZE" ]; then
            mv "$LOG" "${LOG}.1"
            touch "$LOG"
            chmod 644 "$LOG"
        fi
    fi
}

log_line() {
    echo "$1" | tee -a "$LOG"
}

get_app() {
    if pgrep -x hudiy >/dev/null 2>&1; then
        echo "HUDIY"
    elif pgrep -x kodi.bin >/dev/null 2>&1; then
        echo "KODI"
    else
        echo "LAUNCHER"
    fi
}

get_bt_state() {
    if bluetoothctl info "$PHONE_MAC" 2>/dev/null | grep -q 'Connected: yes'; then
        echo "CONNECTED"
    else
        echo "DISCONNECTED"
    fi
}

get_bluez_tree() {
    busctl tree org.bluez 2>/dev/null
}

dump_failure_context() {
    log_line "----- FEHLERKONTEXT START -----"

    {
        echo
        echo "### bluetoothctl info"
        bluetoothctl info "$PHONE_MAC" 2>/dev/null

        echo
        echo "### BlueZ Tree"
        busctl tree org.bluez 2>/dev/null | \
            grep -E "$DEVICE_PATH|player|sep|fd"

        echo
        echo "### PipeWire / WirePlumber"
        ps -eo pid,ppid,etime,cmd | \
            grep -E 'pipewire|wireplumber' | \
            grep -v grep

        echo
        echo "### wpctl"
        XDG_RUNTIME_DIR=/run/user/1000 \
        wpctl status 2>/dev/null | \
            grep -E 'S24 von Sebastian|bluez_input|bluez_output|hudiy|echo_cancel|equalizer'

        echo
        echo "### Journal letzte 15 Sekunden"
        journalctl \
            -b \
            --since "-15 seconds" \
            --no-pager \
            -o short-precise | \
            grep -iE \
            'bluetoothd|wireplumber|pipewire|a2dp|endpoint|bluez|kodi|hudiy'

        echo
    } >> "$LOG"

    log_line "----- FEHLERKONTEXT ENDE -----"
}

touch "$LOG"
chmod 644 "$LOG"

log_line ""
log_line "============================================================"
log_line "$(date '+%Y-%m-%d %H:%M:%S') | A2DP WATCHER GESTARTET"
log_line "============================================================"

while true; do
    rotate_log

    TIME="$(date '+%Y-%m-%d %H:%M:%S')"

    APP="$(get_app)"
    BT="$(get_bt_state)"

    TREE="$(get_bluez_tree)"

    if echo "$TREE" | grep -q "$DEVICE_PATH/player"; then
        PLAYER="PLAYER"
    else
        PLAYER="NO_PLAYER"
    fi

    if echo "$TREE" | grep -q "$DEVICE_PATH/sep"; then
        SEP="SEP"
    else
        SEP="NO_SEP"
    fi

    if echo "$TREE" | grep -q "$DEVICE_PATH/.*/fd"; then
        FD="FD"
    else
        FD="NO_FD"
    fi

    STATE="$APP | $BT | $PLAYER | $SEP | $FD"

    if [ "$STATE" != "$LAST_STATE" ]; then
        log_line "$TIME | $STATE"

        if [ "$BT" = "CONNECTED" ] && \
           { [ "$PLAYER" = "NO_PLAYER" ] || [ "$SEP" = "NO_SEP" ]; }; then

            log_line "$TIME | !!! A2DP FEHLER ERKANNT !!!"
            dump_failure_context
        fi

        LAST_STATE="$STATE"
    fi

    sleep 1
done
