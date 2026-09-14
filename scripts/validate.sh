#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
expected_upstream=fc55f347d6775fcdf4a29bee8680ee5e255d4eb1

actual_upstream=$(git -C "$repo_dir/vendor/indi-allsky" rev-parse HEAD)
if [ "$actual_upstream" != "$expected_upstream" ]; then
    printf 'Unexpected indi-allsky revision: %s (expected %s)\n' "$actual_upstream" "$expected_upstream" >&2
    exit 1
fi

if [ -n "$(git -C "$repo_dir/vendor/indi-allsky" status --porcelain)" ]; then
    printf 'The indi-allsky submodule contains local changes.\n' >&2
    exit 1
fi

ALLSKY_SERVER_ENV_FILE=./deploy/server.env.example \
    docker compose --project-directory "$repo_dir" -f "$repo_dir/compose.yml" config --quiet

printf 'yanoastro_allsky configuration is valid.\n'

