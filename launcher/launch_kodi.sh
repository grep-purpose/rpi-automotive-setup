#!/bin/bash

export HOME=/home/pi
export XDG_RUNTIME_DIR=/run/user/1000
export WAYLAND_DISPLAY=wayland-0

echo "Stopping HUDIY..."

pkill -x hudiy 2>/dev/null || true

sleep 0.5

echo "Starting Kodi..."

exec kodi --standalone
