#!/bin/sh
set -eu

umask 077

target=${1:-/srv/yanoa/secrets/yanoastro_allsky/server.env}
admin_user=${ALLSKY_ADMIN_USER:-dirk}
admin_name=${ALLSKY_ADMIN_NAME:-Dirk Smeets}
admin_email=${ALLSKY_ADMIN_EMAIL:-dirk.smeets@yanoa.be}

target_dir=$(dirname "$target")
mkdir -p "$target_dir"
chmod 700 "$target_dir"

if [ -e "$target" ]; then
    printf 'Refusing to overwrite existing secret file: %s\n' "$target" >&2
    exit 1
fi

flask_secret=$(openssl rand -hex 32)
password_key=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n')
database_password=$(openssl rand -base64 36 | tr -d '\n')
admin_password=${ALLSKY_ADMIN_PASSWORD:-$(openssl rand -base64 24 | tr -d '\n')}
temporary=$(mktemp "$target_dir/server.env.XXXXXX")
trap 'rm -f "$temporary"' EXIT HUP INT TERM

{
    printf 'TZ=Europe/Brussels\n'
    printf 'INDIALLSKY_IMAGE_FOLDER=/var/www/html/allsky/images\n'
    printf 'INDIALLSKY_FLASK_AUTH_ALL_VIEWS=false\n'
    printf 'INDIALLSKY_FLASK_SECRET_KEY=%s\n' "$flask_secret"
    printf 'INDIALLSKY_FLASK_PASSWORD_KEY=%s\n' "$password_key"
    printf 'INDIALLSKY_WEB_USER=%s\n' "$admin_user"
    printf 'INDIALLSKY_WEB_PASS=%s\n' "$admin_password"
    printf 'INDIALLSKY_WEB_NAME=%s\n' "$admin_name"
    printf 'INDIALLSKY_WEB_EMAIL=%s\n' "$admin_email"
    printf 'INDIALLSKY_WEB_GENERATE_APIKEY=false\n'
    printf 'INDIALLSKY_MARIADB_HOST=mariadb.indi.allsky\n'
    printf 'INDIALLSKY_MARIADB_PORT=3306\n'
    printf 'INDIALLSKY_MARIADB_SSL=false\n'
    printf 'INDIALLSKY_MARIADB_CHARSET=utf8mb4\n'
    printf 'INDIALLSKY_MARIADB_COLLATION=utf8mb4_unicode_ci\n'
    printf 'MARIADB_RANDOM_ROOT_PASSWORD=yes\n'
    printf 'MARIADB_DATABASE=indi_allsky\n'
    printf 'MARIADB_USER=indi_allsky_own\n'
    printf 'MARIADB_PASSWORD=%s\n' "$database_password"
    printf 'MARIADB_BACKUP_RETENTION_DAYS=14\n'
    printf 'FORWARDED_ALLOW_IPS=*\n'
} >"$temporary"

chmod 600 "$temporary"
mv "$temporary" "$target"
trap - EXIT HUP INT TERM

printf 'Created %s\n' "$target"
printf 'The generated admin password is stored only in that protected file.\n'

