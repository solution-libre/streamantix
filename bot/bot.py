"""Twitch bot definition and command handlers."""

import math
import pathlib
import random
import re

from twitchio.ext import commands

from bot.cooldown import GlobalCooldown
from game.state import Difficulty, GameState
from game.word_utils import load_word_list

_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
_WORD_LIST_FILES: dict[Difficulty, pathlib.Path] = {
    Difficulty.EASY: _DATA_DIR / "interest_words_f.txt",
    Difficulty.MEDIUM: _DATA_DIR / "interest_words_d.txt",
    Difficulty.HARD: _DATA_DIR / "interest_words_d.txt",
}

_HELP_TEXT = (
    "Commands: "
    "help — show this message | "
    "start [easy|medium|hard] — start a new game (broadcaster only) | "
    "guess <word> — submit a guess | "
    "setprefix <prefix> — change prefix (mod/broadcaster) | "
    "setcooldown <seconds> — change cooldown (mod/broadcaster)"
)

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
    async def help(self, ctx: commands.Context) -> None:
        """Show available commands.

        Usage: <prefix> help
        """
        await ctx.send(_HELP_TEXT)

    @commands.command()
    async def start(self, ctx: commands.Context, difficulty: str = "") -> None:
        """Start a new game round (broadcaster only).

        Usage: <prefix> start [easy|medium|hard]

        If no difficulty is provided, defaults to easy.
        """
        if not ctx.author.is_broadcaster:
            await ctx.send("Only the broadcaster can start a new game.")
            return

        if difficulty:
            try:
                diff = Difficulty(difficulty.lower())
            except ValueError:
                valid = ", ".join(d.value for d in Difficulty)
                await ctx.send(f"Invalid difficulty. Choose from: {valid}")
                return
        else:
            diff = Difficulty.EASY

        word_list_path = _WORD_LIST_FILES[diff]
        try:
            words = load_word_list(word_list_path)
        except FileNotFoundError:
            await ctx.send("Word list not found. Cannot start game.")
            return

        if not words:
            await ctx.send("Word list is empty. Cannot start game.")
            return

        target = random.choice(words)
        self._game_state.start_new_game(target, diff)
        await ctx.send(
            f"A new {diff.value} game has started! "
            f"Guess the secret word using '{self._command_prefix} guess <word>'."
        )

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
