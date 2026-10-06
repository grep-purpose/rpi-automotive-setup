#!/bin/bash

# ============================================================
# RNS-E Bluetooth Autoconnect V3
#
# Reihenfolge:
# 1. S24 von Sebastian
# 2. iPhone als Fallback
#
# Besonderheit:
# Nach erfolgreichem A2DP-Aufbau bleibt das Script noch
# 90 Sekunden aktiv und repariert einen frühen A2DP-Abbruch.
# ============================================================

PHONES=(
    "F4:2B:8C:23:CD:78"
    "D0:3F:AA:D8:71:52"
)

A2DP_UUID="0000110a-0000-1000-8000-00805f9b34fb"

BOOT_GUARD_SECONDS=90


log()
{
    echo "[RNSE Bluetooth] $*"
}


phone_path_from_mac()
{
    echo "dev_${1//:/_}"
}


phone_connected()
{
    local mac="$1"

    bluetoothctl info "$mac" 2>/dev/null \
        | grep -q "Connected: yes"
}


a2dp_objects_ready()
{
    local mac="$1"
    local phone_path
    local tree

    phone_path="$(phone_path_from_mac "$mac")"

    tree="$(
        busctl tree org.bluez 2>/dev/null
    )"

    echo "$tree" \
        | grep -q \
        "/org/bluez/hci0/${phone_path}/player" \
        || return 1

    echo "$tree" \
        | grep -q \
        "/org/bluez/hci0/${phone_path}/sep" \
        || return 1

    return 0
}


request_a2dp()
{
    local mac="$1"
    local phone_path

    phone_path="$(phone_path_from_mac "$mac")"

    log "Fordere A2DP-Profil für $mac an."

    busctl call \
        org.bluez \
        "/org/bluez/hci0/${phone_path}" \
        org.bluez.Device1 \
        ConnectProfile \
        s \
        "$A2DP_UUID" \
        >/dev/null 2>&1 || true
}


wait_for_a2dp()
{
    local mac="$1"

    log "Warte auf A2DP-Objekte."

    for i in $(seq 1 20); do

        if a2dp_objects_ready "$mac"; then
            log "A2DP-Objekte für $mac vorhanden."
            return 0
        fi

        sleep 1
    done

    return 1
}


connect_phone()
{
    local mac="$1"

    log "Versuche Gerät $mac zu verbinden."

    bluetoothctl trust "$mac" \
        >/dev/null 2>&1 || true

    # Wichtig:
    # bluetoothctl darf uns nicht unbegrenzt blockieren.
    timeout 12s \
        bluetoothctl connect "$mac" \
        >/dev/null 2>&1 || true

    sleep 2

    if ! phone_connected "$mac"; then
        log "Gerät $mac nicht erreichbar."
        return 1
    fi

    log "Gerät $mac ist verbunden."

    request_a2dp "$mac"

    if wait_for_a2dp "$mac"; then
        log "A2DP für $mac hergestellt."
        return 0
    fi

    # Ein zweiter kontrollierter Versuch.
    log "A2DP noch nicht bereit - zweiter Versuch."

    request_a2dp "$mac"

    if wait_for_a2dp "$mac"; then
        log "A2DP für $mac im zweiten Versuch hergestellt."
        return 0
    fi

    log "A2DP für $mac konnte nicht hergestellt werden."

    return 1
}


guard_a2dp()
{
    local mac="$1"
    local elapsed=0
    local failures=0

    log "Starte ${BOOT_GUARD_SECONDS}s Boot-Guard für A2DP."

    while [ "$elapsed" -lt "$BOOT_GUARD_SECONDS" ]; do

        sleep 2
        elapsed=$((elapsed + 2))

        # Smartphone selbst weg?
        if ! phone_connected "$mac"; then
            log "Smartphone während Boot-Guard getrennt."
            return 0
        fi

        # Alles weiterhin gesund.
        if a2dp_objects_ready "$mac"; then
            continue
        fi

        failures=$((failures + 1))

        log "A2DP während Boot-Guard verloren."
        log "Reparaturversuch $failures."

        request_a2dp "$mac"

        if wait_for_a2dp "$mac"; then
            log "A2DP erfolgreich wiederhergestellt."
        else
            log "A2DP-Reparaturversuch fehlgeschlagen."
        fi

        # Keine aggressive Endlosschleife.
        if [ "$failures" -ge 3 ]; then
            log "Maximale Anzahl Reparaturversuche erreicht."
            return 0
        fi

    done

    log "Boot-Guard beendet. A2DP blieb stabil."

    return 0
}


log "Starte Multi-Phone Bluetooth-Autoconnect V3."

bluetoothctl power on \
    >/dev/null 2>&1 || true


log "Warte auf registrierten A2DP-Endpunkt."

READY=0

for i in $(seq 1 60); do

    if journalctl \
        -b \
        --no-pager \
        -u bluetooth.service \
        2>/dev/null \
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


ACTIVE_PHONE=""


# ------------------------------------------------------------
# Bevorzugtes Telefon dynamisch berücksichtigen
# ------------------------------------------------------------

PREFERRED_FILE="/home/pi/.kodi/userdata/rnse_bluetooth_preferred.json"
AUTOSTART_FILE="/home/pi/.config/rnse-bluetooth/autoconnect_devices"

PREFERRED_MAC=""

if [ -f "$PREFERRED_FILE" ]; then
    PREFERRED_MAC="$(
        python3 - "$PREFERRED_FILE" <<'PYJSON'
import json
import sys

try:
    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        data = json.load(handle)

    print(
        str(data.get("mac", ""))
        .strip()
        .upper()
    )
except Exception:
    pass
PYJSON
    )"
fi

phone_allowed()
{
    local mac="$1"

    # Falls noch keine Autostart-Datei existiert:
    # bisheriges Verhalten beibehalten.
    if [ ! -f "$AUTOSTART_FILE" ]; then
        return 0
    fi

    grep -Fxiq \
        "$mac" \
        "$AUTOSTART_FILE"
}

PHONE_ORDER=()

add_phone_once()
{
    local mac="$1"
    local known
    local existing

    [ -n "$mac" ] || return 0

    known=0

    for existing in "${PHONES[@]}"; do
        if [ "$existing" = "$mac" ]; then
            known=1
            break
        fi
    done

    [ "$known" -eq 1 ] || return 0
    phone_allowed "$mac" || return 0

    for existing in "${PHONE_ORDER[@]}"; do
        if [ "$existing" = "$mac" ]; then
            return 0
        fi
    done

    PHONE_ORDER+=("$mac")
}

# 1. Bevorzugtes Telefon zuerst
add_phone_once "$PREFERRED_MAC"

# 2. Danach alle übrigen bekannten Telefone als Fallback
for PHONE_MAC in "${PHONES[@]}"; do
    add_phone_once "$PHONE_MAC"
done

if [ -n "$PREFERRED_MAC" ]; then
    log "Bevorzugtes Telefon: $PREFERRED_MAC"
else
    log "Kein bevorzugtes Telefon festgelegt."
fi

log "Autoconnect-Reihenfolge: ${PHONE_ORDER[*]}"

for PHONE_MAC in "${PHONE_ORDER[@]}"; do

    if connect_phone "$PHONE_MAC"; then
        ACTIVE_PHONE="$PHONE_MAC"
        break
    fi

done


if [ -z "$ACTIVE_PHONE" ]; then
    log "WARNUNG: Kein bekanntes Smartphone konnte verbunden werden."
    exit 0
fi


log "Autoconnect erfolgreich für $ACTIVE_PHONE."

guard_a2dp "$ACTIVE_PHONE"

log "Bluetooth Boot-Phase erfolgreich beendet."

exit 0
