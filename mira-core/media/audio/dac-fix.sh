#!/bin/bash
export XDG_RUNTIME_DIR=/run/user/$(id -u)
sleep 8
/usr/bin/wpctl clear-default
DAC_ID=$(wpctl status | grep 'Built-in Audio Stereo' | grep -oE '[0-9]+\.' | tr -d '.')
if [ ! -z "$DAC_ID" ]; then
    /usr/bin/wpctl set-default "$DAC_ID"
    /usr/bin/wpctl set-volume "$DAC_ID" 0.50
    /usr/bin/wpctl set-mute "$DAC_ID" 0
    sleep 1
    /usr/bin/pw-play /home/pi/Audi_Heartbeat_New.wav
fi
