"""Configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable '{name}' is not set. Check your .env file.")
    return value


TWITCH_TOKEN: str = _require("TWITCH_TOKEN")
TWITCH_CHANNEL: str = _require("TWITCH_CHANNEL")
COMMAND_PREFIX: str = os.getenv("COMMAND_PREFIX", "!sx")
COOLDOWN: int = int(os.getenv("COOLDOWN", "5"))
DIFFICULTY: str = os.getenv("DIFFICULTY", "easy")
MODEL_PATH: str = os.getenv(
    "MODEL_PATH", "models/frWac_no_postag_no_phrase_700_skip_cut50.bin"
)
