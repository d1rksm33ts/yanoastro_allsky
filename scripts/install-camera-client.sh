#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this installer with sudo." >&2
    exit 1
fi

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
boot_config=/boot/firmware/config.txt

install -d -o root -g root -m 0755 /usr/local/lib/yanoa-allsky
install -o root -g root -m 0755 "$repo_dir/client/weather_receiver.py" /usr/local/lib/yanoa-allsky/
install -o root -g root -m 0755 "$repo_dir/client/climate_control.py" /usr/local/lib/yanoa-allsky/
install -o root -g root -m 0755 "$repo_dir/client/setup_fan_pwm.sh" /usr/local/lib/yanoa-allsky/

install -o root -g root -m 0644 "$repo_dir/deploy/systemd/yanoa-weather-receiver.service" /etc/systemd/system/
install -o root -g root -m 0644 "$repo_dir/deploy/systemd/yanoa-fan-pwm-setup.service" /etc/systemd/system/
install -o root -g root -m 0644 "$repo_dir/deploy/systemd/yanoa-climate.service" /etc/systemd/system/

if ! grep -Eq '^dtoverlay=w1-gpio([,[:space:]]|$)' "$boot_config"; then
    printf '\ndtoverlay=w1-gpio\n' >> "$boot_config"
fi
if ! grep -Eq '^dtoverlay=pwm,pin=18,func=2([,[:space:]]|$)' "$boot_config"; then
    printf 'dtoverlay=pwm,pin=18,func=2\n' >> "$boot_config"
fi

if [ -f /etc/yanoa-weather/tls/key.pem ]; then
    chown root:smeets /etc/yanoa-weather/tls /etc/yanoa-weather/tls/*.pem
    chmod 0750 /etc/yanoa-weather/tls
    chmod 0640 /etc/yanoa-weather/tls/*.pem
else
    echo "Weather TLS files are not installed; receiver will remain stopped." >&2
fi

systemctl daemon-reload
systemctl enable yanoa-weather-receiver.service yanoa-fan-pwm-setup.service yanoa-climate.service

echo "Camera client services installed. Reboot before starting climate control."
