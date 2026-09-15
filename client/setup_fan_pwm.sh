#!/bin/sh
set -eu

chip=/sys/class/pwm/pwmchip0
channel="$chip/pwm0"

/usr/bin/pinctrl set 18 a5

if [ ! -d "$channel" ]; then
    echo 0 > "$chip/export"
    count=0
    while [ ! -d "$channel" ] && [ "$count" -lt 50 ]; do
        sleep 0.02
        count=$((count + 1))
    done
fi

test -d "$channel"
if [ "$(cat "$channel/enable")" = 1 ]; then
    echo 0 > "$channel/enable"
fi
echo 40000 > "$channel/period"
echo 0 > "$channel/duty_cycle"
echo 1 > "$channel/enable"
chgrp gpio "$channel/duty_cycle"
chmod 0660 "$channel/duty_cycle"
