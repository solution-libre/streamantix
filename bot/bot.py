"""Twitch bot definition and command handlers."""

import re

from twitchio.ext import commands

_MAX_PREFIX_LEN = 10
# No whitespace allowed in prefix
_VALID_PREFIX_RE = re.compile(r"^\S+$")


def _validate_prefix(prefix: str | None) -> str | None:
    """Return an error message string if *prefix* is invalid, else ``None``."""
    if not prefix:
        return "prefix cannot be empty"
    if len(prefix) > _MAX_PREFIX_LEN:
        return f"prefix must be at most {_MAX_PREFIX_LEN} characters"
    if not _VALID_PREFIX_RE.match(prefix):
        return "prefix must not contain whitespace"
    return None


class StreamantixBot(commands.Bot):
    """Streamantix Twitch bot.

    Handles chat commands and delegates game logic to the game engine.
    """

    def __init__(self, **kwargs: object) -> None:
        initial_prefix: str = kwargs.pop("prefix", "!sx")  # type: ignore[assignment]
        self._command_prefix: str = initial_prefix
        super().__init__(prefix=lambda bot, msg: bot._command_prefix, **kwargs)

    async def event_ready(self) -> None:
        """Called once the bot has successfully connected to Twitch."""
        print(f"Logged in as {self.nick}")

    @commands.command()
    async def guess(self, ctx: commands.Context) -> None:
        """Accept a word guess from a chat participant.

        Usage: <prefix> guess <word>
        """
        # TODO: implement guess handling using game.engine
        await ctx.send("Guess command not yet implemented.")

    @commands.command()
    async def setprefix(self, ctx: commands.Context, new_prefix: str = "") -> None:
        """Change the command prefix for this session (moderators and broadcaster only).

        Usage: <prefix> setprefix <new_prefix>

        The change is applied immediately for all subsequent commands but is
        not persisted to the configuration file; it resets when the bot restarts.
        """
        if not (ctx.author.is_mod or ctx.author.is_broadcaster):
            await ctx.send(
                "Only moderators and the broadcaster can change the command prefix."
            )
            return

        error = _validate_prefix(new_prefix)
        if error:
            await ctx.send(f"Invalid prefix: {error}")
            return

        old = self._command_prefix
        self._command_prefix = new_prefix
        await ctx.send(
            f"Command prefix changed from '{old}' to '{new_prefix}' (session only)."
        )
