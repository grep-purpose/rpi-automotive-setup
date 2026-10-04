#!/bin/bash

PHONE_MAC="F4:2B:8C:23:CD:78"
PHONE_PATH="dev_F4_2B_8C_23_CD_78"
A2DP_UUID="0000110a-0000-1000-8000-00805f9b34fb"

export HOME=/home/pi
export XDG_RUNTIME_DIR=/run/user/1000


log()
{
    echo "[RNSE Bluetooth] $*"
}


phone_connected()
{
    bluetoothctl info "$PHONE_MAC" 2>/dev/null \
        | grep -q "Connected: yes"
}


a2dp_ready()
{
    local tree

    tree="$(busctl tree org.bluez 2>/dev/null)"

    echo "$tree" \
        | grep -q "/org/bluez/hci0/${PHONE_PATH}/player" \
        || return 1

    echo "$tree" \
        | grep -q "/org/bluez/hci0/${PHONE_PATH}/sep" \
        || return 1

    return 0
}


bluez_a2dp_endpoints_ready()
{
    busctl tree org.bluez 2>/dev/null \
        | grep -q "/org/bluez/hci0"
}


connect_a2dp_profile()
{
    busctl call \
        org.bluez \
        "/org/bluez/hci0/${PHONE_PATH}" \
        org.bluez.Device1 \
        ConnectProfile \
        s \
        "$A2DP_UUID" \
        >/dev/null 2>&1
}


user_audio()
{
    sudo -u pi \
        XDG_RUNTIME_DIR=/run/user/1000 \
        HOME=/home/pi \
        "$@"
}


ensure_a2dp()
{
    if a2dp_ready; then
        return 0
    fi

    if ! phone_connected; then
        bluetoothctl connect "$PHONE_MAC" \
            >/dev/null 2>&1 || true

        sleep 3
    fi

    if ! phone_connected; then
        return 1
    fi

    connect_a2dp_profile || true

    for i in $(seq 1 8); do
        sleep 1

        if a2dp_ready; then
            return 0
        fi
    done

    return 1
}


log "Starte Bluetooth-Autoconnect."

bluetoothctl power on >/dev/null 2>&1 || true
bluetoothctl trust "$PHONE_MAC" >/dev/null 2>&1 || true


# ============================================================
# PIPEWIRE / WIREPLUMBER ABWARTEN
# ============================================================

log "Warte auf PipeWire / WirePlumber ..."

AUDIO_READY=0

for i in $(seq 1 60); do

    if [ -S /run/user/1000/pipewire-0 ] \
       && user_audio systemctl --user is-active --quiet pipewire.service \
       && user_audio systemctl --user is-active --quiet wireplumber.service \
       && user_audio systemctl --user is-active --quiet pipewire-pulse.service
    then
        AUDIO_READY=1
        break
    fi

    sleep 1
done


if [ "$AUDIO_READY" -ne 1 ]; then
    log "WARNUNG: Audio-Stack wurde nicht rechtzeitig bereit."
    exit 0
fi


log "Audio-Stack ist bereit."

# WirePlumber nicht nur 'running', sondern etwas Initialisierungszeit geben
sleep 5


# ============================================================
# ERSTE VERBINDUNG
# ============================================================

if ensure_a2dp; then
    log "Telefon + A2DP initial erfolgreich verbunden."
else
    log "A2DP initial noch nicht verfügbar."
fi


# ============================================================
# BOOT-STABILITÄTSÜBERWACHUNG
#
# WirePlumber registriert seine BlueZ-Endpunkte während des
# frühen Boots teilweise noch einmal neu.
#
# Deshalb 120 Sekunden lang beobachten und A2DP bei Bedarf
# automatisch wiederherstellen.
# ============================================================

log "Starte A2DP-Stabilitätsprüfung für 120 Sekunden."

LAST_STATE=""

for i in $(seq 1 120); do

    if a2dp_ready; then

        if [ "$LAST_STATE" != "up" ]; then
            log "A2DP ist aktiv."
            LAST_STATE="up"
        fi

    else

        if [ "$LAST_STATE" != "down" ]; then
            log "A2DP fehlt -> Wiederherstellung."
            LAST_STATE="down"
        fi

        if phone_connected; then
            connect_a2dp_profile || true
        else
            bluetoothctl connect "$PHONE_MAC" \
                >/dev/null 2>&1 || true
        fi

    fi

    sleep 1
done


# ============================================================
# ABSCHLUSSPRÜFUNG
# ============================================================

if a2dp_ready; then
    log "A2DP nach Stabilitätsphase dauerhaft verfügbar."
    exit 0
fi


log "WARNUNG: A2DP am Ende der Stabilitätsphase nicht verfügbar."

exit 0
