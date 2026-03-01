"""Twitch bot definition and command handlers."""

from twitchio.ext import commands


class StreamantixBot(commands.Bot):
    """Streamantix Twitch bot.

    Handles chat commands and delegates game logic to the game engine.
    """

    async def event_ready(self) -> None:
        """Called once the bot has successfully connected to Twitch."""
        print(f"Logged in as {self.nick}")

    @commands.command()
    async def guess(self, ctx: commands.Context) -> None:
        """Accept a word guess from a chat participant.

        Usage: !sx guess <word>
        """
        # TODO: implement guess handling using game.engine
        await ctx.send("Guess command not yet implemented.")
