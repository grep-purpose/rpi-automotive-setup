#!/bin/sh
# MIRA: Start the animation as soon as labwc's Wayland socket is available.

HOME=/home/pi
XDG_RUNTIME_DIR=/run/user/1000
WAYLAND_DISPLAY=wayland-0
QT_QPA_PLATFORM=wayland
QT_WAYLAND_DISABLE_WINDOWDECORATION=1

export HOME XDG_RUNTIME_DIR WAYLAND_DISPLAY
export QT_QPA_PLATFORM QT_WAYLAND_DISABLE_WINDOWDECORATION

READY=/run/user/1000/mira-launcher-ready
SOCKET="$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY"

# Wait up to 20 seconds for the compositor socket.
i=0
while [ ! -S "$SOCKET" ] && [ "$i" -lt 200 ]; do
    sleep 0.1
    i=$((i + 1))
done

if [ ! -S "$SOCKET" ]; then
    echo "MIRA: Wayland socket did not appear: $SOCKET"
    exit 1
fi

# Retry if Qt connects before labwc is fully ready.
attempt=0
while [ ! -e "$READY" ] && [ "$attempt" -lt 6 ]; do
    /usr/bin/timeout 5s /usr/bin/python3 \
        /home/pi/rpi-automotive-setup/launcher/mira_transition.py
    result=$?

    if [ -e "$READY" ]; then
        exit 0
    fi

    echo "MIRA: transition attempt $attempt ended (status $result); retrying."
    sleep 0.25
    attempt=$((attempt + 1))
done

echo "MIRA: transition helper stopped before launcher-ready marker appeared."
