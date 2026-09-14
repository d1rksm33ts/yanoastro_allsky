#!/bin/bash
set -Eeuo pipefail

umask 077

backup_dir=${ALLSKY_LEGACY_BACKUP_DIR:-/home/smeets/migration-backup}
stamp=$(date -u +%Y%m%dT%H%M%SZ)
archive="$backup_dir/yanoastro-legacy-$stamp.tar.gz"
temporary="$archive.tmp"
metadata_dir=$(mktemp -d)

cleanup() {
    rm -rf "$metadata_dir"
    rm -f "$temporary"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$backup_dir"
chmod 700 "$backup_dir"

dpkg-query -W -f='${binary:Package}\t${Version}\n' >"$metadata_dir/packages.tsv"
python3 -m pip freeze >"$metadata_dir/python-packages.txt" 2>/dev/null || true
systemctl list-unit-files --no-pager >"$metadata_dir/systemd-unit-files.txt"
systemctl list-timers --all --no-pager >"$metadata_dir/systemd-timers.txt"
crontab -l >"$metadata_dir/user-crontab.txt" 2>/dev/null || true
findmnt -rn -o SOURCE,TARGET,FSTYPE,OPTIONS >"$metadata_dir/mounts.txt"
lsblk -o NAME,SIZE,FSTYPE,UUID,MOUNTPOINTS >"$metadata_dir/block-devices.txt"

if git -C /home/smeets/allsky rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C /home/smeets/allsky status --short >"$metadata_dir/legacy-git-status.txt"
    git -C /home/smeets/allsky rev-parse HEAD >"$metadata_dir/legacy-git-revision.txt"
    git -C /home/smeets/allsky diff --binary >"$metadata_dir/legacy-uncommitted.patch"
fi

mkdir -p "$metadata_dir/representative-images"
latest_working=$(find /home/smeets/allsky/tmp -maxdepth 1 -type f \
    \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) \
    -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -n 1 | cut -d' ' -f2-)
latest_archived=$(find /home/smeets/allsky/images -type f \
    \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) \
    -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -n 1 | cut -d' ' -f2-)

if [[ -n "$latest_working" ]]; then
    cp -a "$latest_working" "$metadata_dir/representative-images/current-${latest_working##*.}"
fi
if [[ -n "$latest_archived" ]]; then
    cp -a "$latest_archived" "$metadata_dir/representative-images/archived-${latest_archived##*.}"
fi

paths=(
    home/smeets/allsky
    home/smeets/control
    home/smeets/logs
    home/smeets/wxcert
    etc/systemd/system
    etc/cron.d
    etc/cron.daily
    etc/cron.hourly
    etc/cron.monthly
    etc/cron.weekly
    etc/crontab
    etc/default
    etc/modules
    boot
)

for optional_path in \
    etc/dhcpcd.conf \
    etc/network \
    etc/NetworkManager/system-connections \
    etc/rc.local \
    var/spool/cron/crontabs/smeets; do
    if [[ -e "/$optional_path" ]]; then
        paths+=("$optional_path")
    fi
done

sudo tar --acls --xattrs --numeric-owner -czf "$temporary" \
    --exclude='home/smeets/allsky/images' \
    --exclude='home/smeets/allsky/tmp' \
    --exclude='home/smeets/control/captures' \
    --exclude='home/smeets/control/previews' \
    --exclude='home/smeets/control/autofocus_work' \
    --exclude='home/smeets/control/__pycache__' \
    --exclude='home/smeets/.cache' \
    -C / "${paths[@]}" \
    -C "${metadata_dir%/*}" "${metadata_dir##*/}"

sudo chown "$(id -u):$(id -g)" "$temporary"
gzip -t "$temporary"
mv "$temporary" "$archive"
(
    cd "$backup_dir"
    sha256sum "${archive##*/}" >"${archive##*/}.sha256"
)

trap - EXIT HUP INT TERM
rm -rf "$metadata_dir"

printf 'Created protected legacy rollback archive: %s\n' "$archive"
printf 'Temporary image archives and caches were excluded.\n'
