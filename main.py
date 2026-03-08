"""Entry point for the streamantix bot."""

import asyncio
import sys

from bot.bot import StreamantixBot
from game.engine import SemanticEngine
import config


def _resolve_token() -> str:
    """Return a valid Twitch access token.

    Resolution order:
    1. ``TWITCH_TOKEN`` env var (manual / legacy).
    2. Stored token file (refresh if near expiry).
    3. Full OAuth login flow (browser redirect).
    """
    if config.TWITCH_TOKEN:
        from auth.twitch_auth import TokenManager, TWITCH_VALIDATE_URL
        import urllib.request

        req = urllib.request.Request(TWITCH_VALIDATE_URL)
        req.add_header("Authorization", f"OAuth {config.TWITCH_TOKEN}")
        try:
            with urllib.request.urlopen(req) as resp:  # noqa: S310
                if resp.status == 200:
                    return config.TWITCH_TOKEN
        except Exception:
            pass
        raise RuntimeError(
            "TWITCH_TOKEN is set but was rejected by Twitch "
            "(expired or revoked). Remove it or set a valid token."
        )

    if not config.TWITCH_CLIENT_ID or not config.TWITCH_CLIENT_SECRET:
        raise RuntimeError(
            "No token available. Set TWITCH_TOKEN, or set TWITCH_CLIENT_ID and "
            "TWITCH_CLIENT_SECRET to enable the OAuth flow."
        )

    from auth.twitch_auth import TokenManager

    manager = TokenManager(
        client_id=config.TWITCH_CLIENT_ID,
        client_secret=config.TWITCH_CLIENT_SECRET,
        redirect_uri=config.TWITCH_REDIRECT_URI,
        scopes=config.TWITCH_SCOPES,
        token_path=config.TWITCH_TOKEN_PATH,
    )
    return manager.get_token()


def main() -> None:
    """Start the Twitch bot, and optionally the overlay server."""
    if len(sys.argv) > 1 and sys.argv[1] == "auth-login":
        # CLI mode: force a new login flow and exit.
        if not config.TWITCH_CLIENT_ID or not config.TWITCH_CLIENT_SECRET:
            raise RuntimeError(
                "TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET must be set for auth-login."
            )
        from auth.twitch_auth import TokenManager

        manager = TokenManager(
            client_id=config.TWITCH_CLIENT_ID,
            client_secret=config.TWITCH_CLIENT_SECRET,
            redirect_uri=config.TWITCH_REDIRECT_URI,
            scopes=config.TWITCH_SCOPES,
            token_path=config.TWITCH_TOKEN_PATH,
        )
        manager.login()
        return

    token = _resolve_token()

    print("Loading Word2Vec model…")
    engine = SemanticEngine(model_path=config.MODEL_PATH)
    engine.load()
    print("Model loaded.")

    if config.OVERLAY_ENABLED:
        from overlay.server import OverlayServer

        async def _run() -> None:
            overlay = OverlayServer(host="0.0.0.0", port=config.OVERLAY_PORT)
            print(f"Overlay available at http://localhost:{config.OVERLAY_PORT}/overlay")
            bot = StreamantixBot(
                token=token,
                prefix=config.COMMAND_PREFIX,
                cooldown=config.COOLDOWN,
                initial_channels=[config.TWITCH_CHANNEL],
                on_state_change=overlay.broadcast,
                scorer=engine,
            )
            await asyncio.gather(bot.start(), overlay.serve())

        asyncio.run(_run())
    else:
        bot = StreamantixBot(
            token=token,
            prefix=config.COMMAND_PREFIX,
            cooldown=config.COOLDOWN,
            initial_channels=[config.TWITCH_CHANNEL],
            scorer=engine,
        )
        bot.run()


if __name__ == "__main__":
    main()
