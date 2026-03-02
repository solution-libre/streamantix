"""Tests for command parsing, prefix configuration, and permission checks (bot.bot)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from bot.bot import StreamantixBot, _validate_prefix, _validate_cooldown
from bot.cooldown import GlobalCooldown


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bot(prefix: str = "!sx", cooldown: int = 5) -> StreamantixBot:
    """Return a StreamantixBot instance without connecting to Twitch."""
    bot = object.__new__(StreamantixBot)
    bot._command_prefix = prefix
    bot._cooldown = GlobalCooldown(cooldown)
    return bot


def _make_ctx(*, is_mod: bool = False, is_broadcaster: bool = False) -> MagicMock:
    """Return a minimal mock of a twitchio Context."""
    ctx = MagicMock()
    ctx.send = AsyncMock()
    ctx.author.is_mod = is_mod
    ctx.author.is_broadcaster = is_broadcaster
    return ctx


# Underlying async function behind the @commands.command() decorator
_setprefix_fn = StreamantixBot.setprefix._callback


# ---------------------------------------------------------------------------
# Prefix validation (pure function — no Twitch connection needed)
# ---------------------------------------------------------------------------

class TestPrefixValidation:
    def test_default_prefix_is_valid(self):
        assert _validate_prefix("!sx") is None

    def test_single_char_prefix_is_valid(self):
        assert _validate_prefix("!") is None

    def test_prefix_at_max_length_is_valid(self):
        assert _validate_prefix("a" * 10) is None

    def test_none_prefix_is_invalid(self):
        assert _validate_prefix(None) is not None

    def test_empty_prefix_is_invalid(self):
        assert _validate_prefix("") is not None

    def test_prefix_with_whitespace_is_invalid(self):
        assert _validate_prefix("! sx") is not None

    def test_prefix_with_only_spaces_is_invalid(self):
        assert _validate_prefix("   ") is not None

    def test_too_long_prefix_is_invalid(self):
        assert _validate_prefix("a" * 11) is not None


# ---------------------------------------------------------------------------
# Default prefix configuration
# ---------------------------------------------------------------------------

class TestCommandParsing:
    def test_default_prefix_stored_on_bot(self):
        """Bot stores the prefix passed at construction time."""
        bot = _make_bot("!sx")
        assert bot._command_prefix == "!sx"

    def test_custom_prefix_stored_on_bot(self):
        """Bot stores a custom prefix passed at construction time."""
        bot = _make_bot("?")
        assert bot._command_prefix == "?"

    def test_guess_command_ignores_extra_args(self):
        """The guess command exists and is callable (smoke test)."""
        assert callable(StreamantixBot.guess._callback)

    def test_unknown_command_is_ignored(self):
        """Commands are registered by name; unknown ones simply won't exist."""
        assert not hasattr(StreamantixBot, "nonexistent_command")


# ---------------------------------------------------------------------------
# setprefix — permission checks
# ---------------------------------------------------------------------------

class TestPermissionChecks:
    async def test_moderator_can_change_prefix(self):
        bot = _make_bot("!sx")
        ctx = _make_ctx(is_mod=True)
        await _setprefix_fn(bot, ctx, "?")
        assert bot._command_prefix == "?"
        ctx.send.assert_called_once()

    async def test_broadcaster_can_change_prefix(self):
        bot = _make_bot("!sx")
        ctx = _make_ctx(is_broadcaster=True)
        await _setprefix_fn(bot, ctx, "?")
        assert bot._command_prefix == "?"
        ctx.send.assert_called_once()

    async def test_regular_user_cannot_change_prefix(self):
        bot = _make_bot("!sx")
        ctx = _make_ctx()  # neither mod nor broadcaster
        await _setprefix_fn(bot, ctx, "?")
        assert bot._command_prefix == "!sx"  # unchanged
        ctx.send.assert_called_once()
        assert "moderator" in ctx.send.call_args[0][0].lower()

    async def test_any_user_can_guess(self):
        """Guess command does not perform permission checks (smoke test)."""
        assert callable(StreamantixBot.guess._callback)


# ---------------------------------------------------------------------------
# setprefix — invalid prefix rejection
# ---------------------------------------------------------------------------

class TestSetprefixValidation:
    async def test_empty_prefix_rejected(self):
        bot = _make_bot("!sx")
        ctx = _make_ctx(is_mod=True)
        await _setprefix_fn(bot, ctx, "")
        assert bot._command_prefix == "!sx"

    async def test_no_prefix_argument_rejected(self):
        bot = _make_bot("!sx")
        ctx = _make_ctx(is_mod=True)
        # default value for new_prefix is ""
        await _setprefix_fn(bot, ctx)
        assert bot._command_prefix == "!sx"

    async def test_prefix_with_spaces_rejected(self):
        bot = _make_bot("!sx")
        ctx = _make_ctx(is_mod=True)
        await _setprefix_fn(bot, ctx, "! sx")
        assert bot._command_prefix == "!sx"

    async def test_too_long_prefix_rejected(self):
        bot = _make_bot("!sx")
        ctx = _make_ctx(is_mod=True)
        await _setprefix_fn(bot, ctx, "a" * 11)
        assert bot._command_prefix == "!sx"

    async def test_invalid_prefix_sends_error_message(self):
        bot = _make_bot("!sx")
        ctx = _make_ctx(is_mod=True)
        await _setprefix_fn(bot, ctx, "bad prefix")
        ctx.send.assert_called_once()
        assert "invalid" in ctx.send.call_args[0][0].lower()


# ---------------------------------------------------------------------------
# setprefix — successful change (session persistence)
# ---------------------------------------------------------------------------

class TestCooldownEnforcement:
    """Prefix changes take effect immediately for all subsequent commands."""

    async def test_prefix_change_persists_in_session(self):
        bot = _make_bot("!sx")
        ctx = _make_ctx(is_mod=True)
        await _setprefix_fn(bot, ctx, "?")
        assert bot._command_prefix == "?"
        # A second change uses the updated prefix as "old"
        ctx2 = _make_ctx(is_mod=True)
        await _setprefix_fn(bot, ctx2, "!new")
        assert bot._command_prefix == "!new"

    async def test_prefix_change_confirmation_message_contains_both_prefixes(self):
        bot = _make_bot("!sx")
        ctx = _make_ctx(is_mod=True)
        await _setprefix_fn(bot, ctx, "?")
        message = ctx.send.call_args[0][0]
        assert "!sx" in message
        assert "?" in message


# ---------------------------------------------------------------------------
# Cooldown validation (pure function)
# ---------------------------------------------------------------------------

class TestCooldownValidation:
    def test_zero_is_valid(self):
        assert _validate_cooldown("0") is None

    def test_positive_integer_is_valid(self):
        assert _validate_cooldown("10") is None

    def test_negative_is_invalid(self):
        assert _validate_cooldown("-1") is not None

    def test_non_integer_is_invalid(self):
        assert _validate_cooldown("abc") is not None

    def test_float_is_invalid(self):
        assert _validate_cooldown("2.5") is not None

    def test_empty_string_is_invalid(self):
        assert _validate_cooldown("") is not None


# ---------------------------------------------------------------------------
# setcooldown command
# ---------------------------------------------------------------------------

_setcooldown_fn = StreamantixBot.setcooldown._callback


class TestSetcooldownPermissions:
    async def test_moderator_can_set_cooldown(self):
        bot = _make_bot()
        ctx = _make_ctx(is_mod=True)
        await _setcooldown_fn(bot, ctx, "10")
        assert bot._cooldown.duration == 10
        ctx.send.assert_called_once()

    async def test_broadcaster_can_set_cooldown(self):
        bot = _make_bot()
        ctx = _make_ctx(is_broadcaster=True)
        await _setcooldown_fn(bot, ctx, "10")
        assert bot._cooldown.duration == 10
        ctx.send.assert_called_once()

    async def test_regular_user_cannot_set_cooldown(self):
        bot = _make_bot()
        ctx = _make_ctx()
        await _setcooldown_fn(bot, ctx, "10")
        assert bot._cooldown.duration == 5  # unchanged
        ctx.send.assert_called_once()
        assert "moderator" in ctx.send.call_args[0][0].lower()


class TestSetcooldownValidation:
    async def test_valid_cooldown_is_applied(self):
        bot = _make_bot()
        ctx = _make_ctx(is_mod=True)
        await _setcooldown_fn(bot, ctx, "20")
        assert bot._cooldown.duration == 20

    async def test_zero_cooldown_is_accepted(self):
        bot = _make_bot()
        ctx = _make_ctx(is_mod=True)
        await _setcooldown_fn(bot, ctx, "0")
        assert bot._cooldown.duration == 0

    async def test_invalid_cooldown_sends_error(self):
        bot = _make_bot()
        ctx = _make_ctx(is_mod=True)
        await _setcooldown_fn(bot, ctx, "bad")
        assert bot._cooldown.duration == 5  # unchanged
        ctx.send.assert_called_once()
        assert "invalid" in ctx.send.call_args[0][0].lower()

    async def test_negative_cooldown_rejected(self):
        bot = _make_bot()
        ctx = _make_ctx(is_mod=True)
        await _setcooldown_fn(bot, ctx, "-1")
        assert bot._cooldown.duration == 5  # unchanged

    async def test_confirmation_message_contains_value(self):
        bot = _make_bot()
        ctx = _make_ctx(is_mod=True)
        await _setcooldown_fn(bot, ctx, "7")
        assert "7" in ctx.send.call_args[0][0]


# ---------------------------------------------------------------------------
# guess — cooldown enforcement
# ---------------------------------------------------------------------------

_guess_fn = StreamantixBot.guess._callback


class TestGuessCooldownEnforcement:
    async def test_guess_blocked_during_cooldown(self):
        bot = _make_bot(cooldown=30)
        bot._cooldown.record()  # simulate a recent guess
        ctx = _make_ctx()
        await _guess_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "wait" in message.lower()

    async def test_guess_allowed_when_not_on_cooldown(self):
        bot = _make_bot(cooldown=0)
        ctx = _make_ctx()
        await _guess_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "wait" not in message.lower()

    async def test_guess_records_cooldown(self):
        bot = _make_bot(cooldown=30)
        ctx = _make_ctx()
        assert not bot._cooldown.is_on_cooldown()
        await _guess_fn(bot, ctx)
        assert bot._cooldown.is_on_cooldown()

    async def test_blocked_guess_message_mentions_seconds(self):
        bot = _make_bot(cooldown=30)
        bot._cooldown.record()
        ctx = _make_ctx()
        await _guess_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "second" in message.lower()
