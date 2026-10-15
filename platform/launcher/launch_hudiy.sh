#!/bin/bash

export HOME=/home/pi
export XDG_RUNTIME_DIR=/run/user/1000
export WAYLAND_DISPLAY=wayland-0

export QT_QPA_PLATFORM=wayland
export QT_WAYLAND_DISABLE_WINDOWDECORATION=1

export LD_LIBRARY_PATH="/home/pi/.hudiy/share:${LD_LIBRARY_PATH}"

echo "Stopping Kodi..."

# Zuerst den /usr/bin/kodi-Wrapper beenden.
# Sonst kann er kodi.bin nach dem Kill erneut starten.
pkill -TERM -f '^/bin/sh /usr/bin/kodi$' 2>/dev/null || true
pkill -TERM -x kodi.bin 2>/dev/null || true

sleep 0.3

# Falls noch etwas übrig geblieben ist, hart entfernen.
pkill -KILL -f '^/bin/sh /usr/bin/kodi$' 2>/dev/null || true
pkill -KILL -x kodi.bin 2>/dev/null || true

sleep 0.5

echo "Starting HUDIY..."

echo "hudiy" > /run/user/1000/rnse_active_app

cd /home/pi/.hudiy/share || exit 1

./hudiy_startup.sh

echo "Waiting for HUDIY..."

for i in $(seq 1 50); do

    if pgrep -x hudiy >/dev/null; then
        break
    fi

    sleep 0.1

done

echo "HUDIY running."

while pgrep -x hudiy >/dev/null; do
    sleep 0.5
done

echo "HUDIY closed."
