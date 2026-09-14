#!/bin/sh
set -eu

umask 077

container=${ALLSKY_APP_CONTAINER:-yanoastro-allsky-app}
username=${ALLSKY_SYNCAPI_USER:-dirk}
target=${ALLSKY_SYNCAPI_KEY_FILE:-/srv/yanoa/secrets/yanoastro_allsky/syncapi.key}
target_dir=$(dirname "$target")

mkdir -p "$target_dir"
chmod 700 "$target_dir"

if [ -e "$target" ]; then
    printf 'Refusing to overwrite existing SyncAPI key file: %s\n' "$target" >&2
    exit 1
fi

output=$(docker exec "$container" \
    /home/allsky/indi-allsky/misc/usertool.py genapikey --username "$username")
apikey=$(printf '%s\n' "$output" | sed -n 's/^API key: //p' | tail -n 1)

if [ "${#apikey}" -ne 64 ]; then
    printf 'Could not extract the generated SyncAPI key.\n' >&2
    exit 1
fi

temporary=$(mktemp "$target_dir/syncapi.key.XXXXXX")
trap 'rm -f "$temporary"' EXIT HUP INT TERM
printf '%s\n' "$apikey" >"$temporary"
chmod 600 "$temporary"
mv "$temporary" "$target"
trap - EXIT HUP INT TERM

unset apikey output
printf 'Generated the SyncAPI key and stored it in %s\n' "$target"
printf 'The key itself was not written to logs.\n'
