"""Configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()

def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable '{name}' is not set. Check your .env file.")
    return value


# Optional: kept for users who still want to supply a token manually.
TWITCH_TOKEN: str | None = os.getenv("TWITCH_TOKEN")
TWITCH_CHANNEL: str = _require("TWITCH_CHANNEL")
COMMAND_PREFIX: str = os.getenv("COMMAND_PREFIX", "!sx")
COOLDOWN: int = int(os.getenv("COOLDOWN", "5"))
DIFFICULTY: str = os.getenv("DIFFICULTY", "easy")
SCORING_TOP_N: int = int(os.getenv("SCORING_TOP_N", "1000"))
MODEL_PATH: str = os.getenv(
    "MODEL_PATH", "models/frWac_no_postag_no_phrase_700_skip_cut50.bin"
)
OVERLAY_ENABLED: bool = os.getenv("OVERLAY_ENABLED", "false").lower() in ("1", "true", "yes")
OVERLAY_PORT: int = int(os.getenv("OVERLAY_PORT", "8080"))

# Twitch OAuth (Authorization Code flow)
TWITCH_CLIENT_ID: str | None = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET: str | None = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_REDIRECT_URI: str = os.getenv("TWITCH_REDIRECT_URI", "http://localhost:4343/callback")
TWITCH_SCOPES: str = os.getenv("TWITCH_SCOPES", "chat:read chat:edit")
TWITCH_TOKEN_PATH: str = os.getenv("TWITCH_TOKEN_PATH", ".secrets/twitch_tokens.json")
