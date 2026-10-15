#!/bin/sh
set -u

HOME=/home/pi
XDG_RUNTIME_DIR=/run/user/1000
WAYLAND_DISPLAY=wayland-0
IMAGE=/usr/share/plymouth/themes/mira/frame-0.png
LOG=/tmp/mira-swaybg-early.log
READY=/run/user/1000/mira-background-ready

export HOME XDG_RUNTIME_DIR WAYLAND_DISPLAY

# Remove any marker from an earlier session.
rm -f "$READY"

i=0
while [ "$i" -lt 200 ]; do
    if [ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]; then
        /usr/bin/logger -t mira-start \
          "EARLY_SWAYBG_SOCKET_READY $(awk '{print $1}' /proc/uptime)"

        /usr/bin/swaybg -i "$IMAGE" -m fill >> "$LOG" 2>&1 &
        BG_PID=$!

        # Allow swaybg time to connect and initialize.
        sleep 0.5

        if kill -0 "$BG_PID" 2>/dev/null; then
            : > "$READY"

            /usr/bin/logger -t mira-start \
              "EARLY_SWAYBG_READY pid=$BG_PID"

            wait "$BG_PID"
            exit $?
        fi

        wait "$BG_PID" || true

        /usr/bin/logger -t mira-start \
          "EARLY_SWAYBG_RETRY attempt=$i"
    fi

    sleep 0.1
    i=$((i + 1))
done

/usr/bin/logger -p daemon.warning -t mira-start \
  "EARLY_SWAYBG_TIMEOUT"

exit 1
