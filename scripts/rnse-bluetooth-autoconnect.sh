#!/bin/bash

# Bevorzugte Reihenfolge:
# 1. S24 von Sebastian
# 2. iPhone als Fallback

PHONES=(
    "F4:2B:8C:23:CD:78"
    "D0:3F:AA:D8:71:52"
)

A2DP_UUID="0000110a-0000-1000-8000-00805f9b34fb"

log()
{
    echo "[RNSE Bluetooth] $*"
}

phone_path_from_mac()
{
    echo "dev_${1//:/_}"
}

a2dp_objects_ready()
{
    local mac="$1"
    local phone_path
    local tree

    phone_path="$(phone_path_from_mac "$mac")"
    tree="$(busctl tree org.bluez 2>/dev/null)"

    echo "$tree" \
        | grep -q "/org/bluez/hci0/${phone_path}/player" \
        || return 1

    echo "$tree" \
        | grep -q "/org/bluez/hci0/${phone_path}/sep" \
        || return 1

    return 0
}

connect_phone_once()
{
    local mac="$1"
    local phone_path

    phone_path="$(phone_path_from_mac "$mac")"

    log "Versuche Gerät $mac zu verbinden."

    bluetoothctl trust "$mac" >/dev/null 2>&1 || true

    bluetoothctl connect "$mac" >/dev/null 2>&1 || true

    sleep 2

    if ! bluetoothctl info "$mac" 2>/dev/null \
        | grep -q "Connected: yes"
    then
        log "Gerät $mac nicht erreichbar."
        return 1
    fi

    log "Gerät $mac ist verbunden."

    log "Fordere A2DP-Profil genau einmal an."

    busctl call \
        org.bluez \
        "/org/bluez/hci0/${phone_path}" \
        org.bluez.Device1 \
        ConnectProfile \
        s \
        "$A2DP_UUID" \
        >/dev/null 2>&1 || true

    log "Warte auf A2DP-Objekte."

    for i in $(seq 1 15); do
        if a2dp_objects_ready "$mac"; then
            log "A2DP für $mac vollständig hergestellt."
            return 0
        fi

        sleep 1
    done

    log "A2DP für $mac wurde nicht vollständig aufgebaut."

    return 1
}

log "Starte Multi-Phone Bluetooth-Autoconnect."

bluetoothctl power on >/dev/null 2>&1 || true

log "Warte auf registrierten A2DP-Endpunkt."

READY=0

for i in $(seq 1 60); do
    if journalctl \
        -b \
        --no-pager \
        -u bluetooth.service 2>/dev/null \
        | grep -q \
        'Endpoint registered:.*MediaEndpoint/A2DPSink/sbc'
    then
        READY=1
        break
    fi

    sleep 1
done

if [ "$READY" -eq 1 ]; then
    log "A2DP-Endpunkt ist bereit."
else
    log "WARNUNG: A2DP-Endpunkt wurde nicht erkannt."
fi

sleep 2

for PHONE_MAC in "${PHONES[@]}"; do
    if connect_phone_once "$PHONE_MAC"; then
        log "Autoconnect erfolgreich beendet."
        exit 0
    fi
done

log "WARNUNG: Kein bekanntes Smartphone konnte verbunden werden."

exit 0
