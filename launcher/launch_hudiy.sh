#!/bin/bash

export HOME=/home/pi
export XDG_RUNTIME_DIR=/run/user/1000
export WAYLAND_DISPLAY=wayland-0

export QT_QPA_PLATFORM=wayland
export QT_WAYLAND_DISABLE_WINDOWDECORATION=1

export LD_LIBRARY_PATH="/home/pi/.hudiy/share:${LD_LIBRARY_PATH}"

echo "Stopping Kodi..."

pkill -x kodi.bin 2>/dev/null || true
pkill -x kodi 2>/dev/null || true

sleep 0.5

echo "Starting HUDIY..."

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
