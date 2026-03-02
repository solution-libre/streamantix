#!/bin/sh
# Download the Word2Vec model if it is not already present, then start the bot.
set -e

python download_model.py
exec python main.py
