#!/bin/sh
# Fix ownership of bind-mounted volumes when started as root, then drop to appuser.
set -e

if [ "$(id -u)" = "0" ]; then
    chown appuser:appuser /app/models /app/.secrets
    exec gosu appuser /app/docker-entrypoint.sh "$@"
fi

python download_model.py
exec python main.py
