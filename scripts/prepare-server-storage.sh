#!/bin/sh
set -eu

yanoa_root=${YANOA_ROOT:-/srv/yanoa}

# The nginx container serves this bind mount read-only. Only traversal/read is
# public; write access remains limited to the indi-allsky application owner.
install -d -m 0755 "$yanoa_root/data/yanoastro_allsky/images"

# Database and migration state are not web content.
install -d -m 0750 "$yanoa_root/data/yanoastro_allsky/database"
install -d -m 0750 "$yanoa_root/data/yanoastro_allsky/migrations"
install -d -m 0750 "$yanoa_root/backups/yanoastro_allsky"
