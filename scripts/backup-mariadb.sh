#!/bin/sh
set -eu

umask 077

backup_dir=/backups
retention_days=${MARIADB_BACKUP_RETENTION_DAYS:-14}
stamp=$(date -u +%Y%m%dT%H%M%SZ)
final="$backup_dir/indi-allsky-$stamp.sql.gz"
temporary="$final.tmp"

mkdir -p "$backup_dir"
trap 'rm -f "$temporary"' EXIT HUP INT TERM

export MYSQL_PWD=$MARIADB_PASSWORD

mariadb-dump \
    --host="$INDIALLSKY_MARIADB_HOST" \
    --port="$INDIALLSKY_MARIADB_PORT" \
    --user="$MARIADB_USER" \
    --single-transaction \
    --routines \
    --events \
    --triggers \
    "$MARIADB_DATABASE" | gzip -9 >"$temporary"

gzip -t "$temporary"
mv "$temporary" "$final"
sha256sum "$final" >"$final.sha256"

find "$backup_dir" -type f \
    \( -name 'indi-allsky-*.sql.gz' -o -name 'indi-allsky-*.sql.gz.sha256' \) \
    -mtime "+$retention_days" -delete

printf 'Created %s\n' "$final"

