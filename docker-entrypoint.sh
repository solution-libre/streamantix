#!/usr/bin/env sh

set -e

# Fix ownership of bind-mounted volumes when started as root, then drop to appuser.
if [ "$(id -u)" = "0" ]; then
    chown appuser:appuser /app/models /app/.secrets
    exec gosu appuser /app/docker-entrypoint.sh "$@"
fi

# Download the Word2Vec model if it is not already present, then start the bot.
python download_model.py
exec python main.py
