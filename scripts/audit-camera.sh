#!/bin/sh
set -eu

umask 077

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
stamp=$(date -u +%Y%m%dT%H%M%SZ)
output_dir="$repo_dir/audit-output/camera-$stamp"
archive="$repo_dir/audit-output/camera-$stamp.tar.gz"

mkdir -p "$output_dir"

capture() {
    name=$1
    shift
    {
        printf '$'
        printf ' %s' "$@"
        printf '\n\n'
        "$@" 2>&1 || true
    } >"$output_dir/$name.txt"
}

capture identity uname -a
capture os-release sh -c 'test -r /etc/os-release && sed -n "1,160p" /etc/os-release'
capture cpu lscpu
capture memory free -h
capture block-devices lsblk -e 7 -o NAME,MODEL,SERIAL,SIZE,FSTYPE,FSVER,FSAVAIL,FSUSE%,MOUNTPOINTS
capture filesystems df -hT
capture mounts findmnt
capture routes ip route show
capture addresses ip -brief address show
capture dns resolvectl status
capture time timedatectl status
capture failed-units systemctl --failed --no-pager
capture services systemctl list-units --type=service --all --no-pager
capture timers systemctl list-timers --all --no-pager
capture cron sh -c 'find /etc/cron.d /etc/cron.daily /etc/cron.hourly /etc/cron.weekly -maxdepth 1 -type f -printf "%p\n" 2>/dev/null | sort'
capture packages sh -c 'dpkg-query -W -f="\${binary:Package}\t\${Version}\n" 2>/dev/null | grep -Ei "allsky|indi|libcamera|rpicam|python|nginx|apache|php|mariadb|mysql"'
capture processes ps auxww
capture listeners ss -lntup
capture usb lsusb
capture video-devices sh -c 'ls -la /dev/video* /dev/media* 2>/dev/null'
capture camera-info sh -c 'command -v rpicam-hello >/dev/null && rpicam-hello --list-cameras || command -v libcamera-hello >/dev/null && libcamera-hello --list-cameras || true'
capture pi-revision sh -c 'test -r /proc/device-tree/model && tr -d "\000" </proc/device-tree/model; echo'
capture pi-throttle sh -c 'command -v vcgencmd >/dev/null && vcgencmd get_throttled || true'
capture pi-temperature sh -c 'command -v vcgencmd >/dev/null && vcgencmd measure_temp || true'
capture allsky-paths sh -c 'find /home /opt /usr/local /var/www -maxdepth 4 \( -iname "*allsky*" -o -iname "*indi*" \) -print 2>/dev/null | sort'
capture large-directories sh -c 'du -x -h -d 2 /home /var 2>/dev/null | sort -h | tail -80'
capture journal-errors journalctl -b -p warning --no-pager -n 500

tar -C "$(dirname "$output_dir")" -czf "$archive" "$(basename "$output_dir")"
printf 'Audit written to %s\n' "$archive"
printf 'Review it before sharing; it may contain private network metadata.\n'
