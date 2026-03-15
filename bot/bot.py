"""Twitch bot definition and command handlers."""

import math
import pathlib
import random
import re
from collections.abc import Awaitable, Callable
from typing import Any

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
    "hint — show top 10 guesses | "
    "status — show current game status | "
    "setprefix <prefix> — change prefix (mod/broadcaster) | "
    "setcooldown <seconds> — change cooldown (mod/broadcaster) | "
    "setdifficulty <easy|hard> — set difficulty for next game (mod/broadcaster)"
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


def _validate_difficulty(value: str | None) -> str | None:
    """Return an error message string if *value* is not a valid setdifficulty value, else ``None``.

    Note: ``setdifficulty`` only accepts ``easy`` and ``hard``.  ``medium`` is
    intentionally excluded here; it remains accessible via the ``start`` command
    for backwards compatibility.
    """
    valid = {Difficulty.EASY.value, Difficulty.HARD.value}
    if not value or value.lower() not in valid:
        return f"difficulty must be one of: {', '.join(sorted(valid))}"
    return None


class StreamantixBot(commands.Bot):
    """Streamantix Twitch bot.

    Handles chat commands and delegates game logic to the game engine.

    Args:
        on_state_change: Optional async callback invoked with a serialised
            game-state dict after each ``start`` or ``guess`` event.  Use this
            to push updates to the overlay server without tight coupling.
    """

    def __init__(self, **kwargs: object) -> None:
        initial_prefix: str = kwargs.pop("prefix", "!sx")  # type: ignore[assignment]
        initial_cooldown: int = kwargs.pop("cooldown", 5)  # type: ignore[assignment]
        on_state_change: Callable[[dict[str, Any]], Awaitable[None]] | None = kwargs.pop(  # type: ignore[assignment]
            "on_state_change", None
        )
        scorer = kwargs.pop("scorer", None)  # type: ignore[assignment]
        self._command_prefix: str = initial_prefix
        self._cooldown = GlobalCooldown(int(initial_cooldown))
        self._game_state = GameState(scorer=scorer)  # type: ignore[arg-type]
        self._on_state_change = on_state_change
        self._next_difficulty: Difficulty = Difficulty.EASY
        super().__init__(prefix=lambda bot, msg: bot._command_prefix, **kwargs)

    async def _notify_overlay(self) -> None:
        """Fire the overlay callback with the current serialised game state."""
        callback = getattr(self, "_on_state_change", None)
        if callback is None:
            return
        from overlay.state import serialize_game_state  # lazy import to avoid hard dep

        await callback(serialize_game_state(self._game_state))

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

    @commands.command(name="start")
    async def start_game(self, ctx: commands.Context, difficulty: str = "") -> None:
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
            diff = self._next_difficulty

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
        await self._notify_overlay()

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

        if result.is_found and not result.already_cited:
            await ctx.send(f"🎉 {ctx.author.name} found the word '{word}'!")
        elif result.is_found and result.already_cited:
            found_by = self._game_state.found_by
            await ctx.send(f"🎉 The word '{word}' was already found by {found_by}!")
        elif result.already_cited:
            if result.entry.score is not None:
                pct = int(result.entry.score * 100)
                await ctx.send(f"'{word}' has already been suggested ({pct}% similarity).")
            else:
                await ctx.send(f"'{word}' has already been suggested.")
        elif result.entry.score is not None:
            pct = int(result.entry.score * 100)
            await ctx.send(f"'{word}': {pct}% similarity")
        else:
            await ctx.send(f"'{word}' is not in the vocabulary.")
        await self._notify_overlay()

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

    @commands.command()
    async def hint(self, ctx: commands.Context) -> None:
        """Show the top 10 best guesses so far (proximity leaderboard).

        Usage: <prefix> hint
        """
        if self._game_state.target_word is None:
            await ctx.send("No game is currently in progress.")
            return

        top = self._game_state.top_guesses(10)
        if not top:
            await ctx.send("No scored guesses yet.")
            return

        parts = [
            f"{i + 1}. {e.raw_word} ({int((e.score or 0.0) * 100)}%)"
            for i, e in enumerate(top)
        ]
        await ctx.send("Top guesses: " + " | ".join(parts))

    @commands.command()
    async def status(self, ctx: commands.Context) -> None:
        """Show the current game status.

        Usage: <prefix> status
        """
        if self._game_state.target_word is None:
            await ctx.send("No game is currently in progress.")
            return

        attempts = self._game_state.attempt_count

        if self._game_state.is_found:
            found_by = self._game_state.found_by
            await ctx.send(
                f"Game over! Word found by {found_by} in {attempts} attempt(s)."
            )
            return

        top = self._game_state.top_guesses(1)
        if top:
            best = top[0]
            pct = int((best.score or 0.0) * 100)
            await ctx.send(
                f"Game in progress. {attempts} attempt(s). "
                f"Best guess: '{best.raw_word}' ({pct}%)."
            )
        else:
            await ctx.send(
                f"Game in progress. {attempts} attempt(s). No scored guesses yet."
            )

    @commands.command()
    async def setdifficulty(self, ctx: commands.Context, difficulty: str = "") -> None:
        """Change the difficulty for the next game (moderators and broadcaster only).

        Usage: <prefix> setdifficulty <easy|hard>

        Does not affect the current game. The change is applied immediately but is
        not persisted; it resets when the bot restarts.
        """
        if not (ctx.author.is_mod or ctx.author.is_broadcaster):
            await ctx.send(
                "Only moderators and the broadcaster can change the difficulty."
            )
            return

        error = _validate_difficulty(difficulty)
        if error:
            await ctx.send(f"Invalid difficulty: {error}")
            return

        self._next_difficulty = Difficulty(difficulty.lower())
        await ctx.send(
            f"Difficulty for the next game set to '{self._next_difficulty.value}' (session only)."
        )
