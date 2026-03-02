"""Entry point for the streamantix bot."""

import asyncio

from bot.bot import StreamantixBot
import config


def main() -> None:
    """Start the Twitch bot, and optionally the overlay server."""
    if config.OVERLAY_ENABLED:
        from overlay.server import OverlayServer

        overlay = OverlayServer(host="0.0.0.0", port=config.OVERLAY_PORT)
        bot = StreamantixBot(
            token=config.TWITCH_TOKEN,
            prefix=config.COMMAND_PREFIX,
            cooldown=config.COOLDOWN,
            initial_channels=[config.TWITCH_CHANNEL],
            on_state_change=overlay.broadcast,
        )

        async def _run() -> None:
            await asyncio.gather(bot.start(), overlay.serve())

        asyncio.run(_run())
    else:
        bot = StreamantixBot(
            token=config.TWITCH_TOKEN,
            prefix=config.COMMAND_PREFIX,
            cooldown=config.COOLDOWN,
            initial_channels=[config.TWITCH_CHANNEL],
        )
        bot.run()


if __name__ == "__main__":
    main()
