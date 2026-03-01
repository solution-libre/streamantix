"""Entry point for the streamantix bot."""

from bot.bot import StreamantixBot
import config


def main() -> None:
    """Start the Twitch bot."""
    bot = StreamantixBot(
        token=config.TWITCH_TOKEN,
        prefix=config.COMMAND_PREFIX,
        initial_channels=[config.TWITCH_CHANNEL],
    )
    bot.run()


if __name__ == "__main__":
    main()
