"""Twitch bot definition and command handlers."""

import math
import re

from twitchio.ext import commands

from bot.cooldown import GlobalCooldown
from game.state import GameState

_MAX_PREFIX_LEN = 10
_MAX_WORD_LEN = 50
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


def _validate_cooldown(value: str) -> str | None:
    """Return an error message string if *value* is not a valid cooldown, else ``None``."""
    try:
        seconds = int(value)
    except (ValueError, TypeError):
        return "cooldown must be a non-negative integer"
    if seconds < 0:
        return "cooldown must be a non-negative integer"
    return None


class StreamantixBot(commands.Bot):
    """Streamantix Twitch bot.

    Handles chat commands and delegates game logic to the game engine.
    """

    def __init__(self, **kwargs: object) -> None:
        initial_prefix: str = kwargs.pop("prefix", "!sx")  # type: ignore[assignment]
        initial_cooldown: int = kwargs.pop("cooldown", 5)  # type: ignore[assignment]
        self._command_prefix: str = initial_prefix
        self._cooldown = GlobalCooldown(int(initial_cooldown))
        self._game_state = GameState()
        super().__init__(prefix=lambda bot, msg: bot._command_prefix, **kwargs)

    async def event_ready(self) -> None:
        """Called once the bot has successfully connected to Twitch."""
        print(f"Logged in as {self.nick}")

    async def event_error(self, error: Exception, data: str | None = None) -> None:
        """Called when an error occurs; logs it without crashing the bot."""
        print(f"Error: {error}")

    @commands.command()
    async def guess(self, ctx: commands.Context, word: str = "") -> None:
        """Accept a word guess from a chat participant.

        Usage: <prefix> guess <word>
        """
        if self._cooldown.is_on_cooldown():
            remaining = math.ceil(self._cooldown.remaining())
            await ctx.send(
                f"Please wait {remaining} seconds before guessing again."
            )
            return

        self._cooldown.record()

        if not word:
            await ctx.send("Please provide a word to guess.")
            return

        if len(word) > _MAX_WORD_LEN:
            await ctx.send(f"Word is too long (max {_MAX_WORD_LEN} characters).")
            return

        try:
            result = self._game_state.submit_guess(ctx.author.name, word)
        except RuntimeError:
            await ctx.send("No game is currently in progress.")
            return

        if result.is_found:
            await ctx.send(f"🎉 {ctx.author.name} found the word '{word}'!")
        elif result.entry.score is not None:
            pct = int(result.entry.score * 100)
            await ctx.send(f"'{word}': {pct}% similarity")
        else:
            await ctx.send(f"'{word}' is not in the vocabulary.")

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

    @commands.command()
    async def setcooldown(self, ctx: commands.Context, seconds: str = "") -> None:
        """Change the guess cooldown duration for this session (moderators and broadcaster only).

        Usage: <prefix> setcooldown <seconds>

        The change is applied immediately but is not persisted; it resets when the bot restarts.
        """
        if not (ctx.author.is_mod or ctx.author.is_broadcaster):
            await ctx.send(
                "Only moderators and the broadcaster can change the cooldown."
            )
            return

        error = _validate_cooldown(seconds)
        if error:
            await ctx.send(f"Invalid cooldown: {error}")
            return

        value = int(seconds)
        self._cooldown.set_duration(value)
        await ctx.send(f"Cooldown set to {value} seconds (session only).")
