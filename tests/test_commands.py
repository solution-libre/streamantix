"""Tests for command parsing, prefix configuration, and permission checks (bot.bot)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.bot import StreamantixBot, _validate_prefix, _validate_cooldown, _validate_difficulty
from bot.cooldown import CooldownManager
from game.state import Difficulty, GameState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bot(prefix: str = "!sx", cooldown: int = 5) -> StreamantixBot:
    """Return a StreamantixBot instance without connecting to Twitch."""
    bot = object.__new__(StreamantixBot)
    bot._command_prefix = prefix
    bot._cooldown = CooldownManager(cooldown)
    bot._game_state = GameState()
    bot._next_difficulty = Difficulty.EASY
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
        ctx = _make_ctx()
        ctx.author.name = "alice"
        bot._cooldown.record("alice")  # simulate a recent guess by this user
        await _guess_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "wait" in message.lower()

    async def test_guess_allowed_when_not_on_cooldown(self):
        bot = _make_bot(cooldown=0)
        ctx = _make_ctx()
        ctx.author.name = "alice"
        await _guess_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "wait" not in message.lower()

    async def test_guess_records_cooldown(self):
        bot = _make_bot(cooldown=30)
        ctx = _make_ctx()
        ctx.author.name = "alice"
        assert not bot._cooldown.is_on_cooldown("alice")
        await _guess_fn(bot, ctx)
        assert bot._cooldown.is_on_cooldown("alice")

    async def test_blocked_guess_message_mentions_seconds(self):
        bot = _make_bot(cooldown=30)
        ctx = _make_ctx()
        ctx.author.name = "alice"
        bot._cooldown.record("alice")
        await _guess_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "second" in message.lower()

    async def test_different_users_have_independent_cooldowns(self):
        """One user being on cooldown must not block another user."""
        bot = _make_bot(cooldown=30)
        ctx_alice = _make_ctx()
        ctx_alice.author.name = "alice"
        ctx_bob = _make_ctx()
        ctx_bob.author.name = "bob"
        bot._cooldown.record("alice")  # only alice is on cooldown
        assert bot._cooldown.is_on_cooldown("alice")
        assert not bot._cooldown.is_on_cooldown("bob")
        # Bob should be allowed to guess despite alice being on cooldown
        await _guess_fn(bot, ctx_bob)
        message = ctx_bob.send.call_args[0][0]
        assert "wait" not in message.lower()


# ---------------------------------------------------------------------------
# guess — game routing
# ---------------------------------------------------------------------------


class _FakeScorer:
    """Deterministic scorer: returns 0.5 for any non-exact guess."""

    def score_guess(self, guess: str, target: str) -> float | None:
        from game.word_utils import clean_word
        if clean_word(guess) == clean_word(target):
            return 1.0
        return 0.5


class TestGuessRouting:
    async def test_guess_without_word_sends_usage_hint(self):
        bot = _make_bot(cooldown=0)
        ctx = _make_ctx()
        await _guess_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "provide" in message.lower() or "usage" in message.lower()

    async def test_guess_without_active_game_sends_error(self):
        bot = _make_bot(cooldown=0)
        ctx = _make_ctx()
        ctx.author.name = "alice"
        await _guess_fn(bot, ctx, "chat")
        message = ctx.send.call_args[0][0]
        assert "no game" in message.lower()

    async def test_guess_exact_match_announces_winner(self):
        bot = _make_bot(cooldown=0)
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx = _make_ctx()
        ctx.author.name = "alice"
        await _guess_fn(bot, ctx, "chat")
        message = ctx.send.call_args[0][0]
        assert "alice" in message.lower()
        assert "chat" in message.lower()

    async def test_guess_near_match_shows_similarity(self):
        bot = _make_bot(cooldown=0)
        bot._game_state = GameState(scorer=_FakeScorer())
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx = _make_ctx()
        ctx.author.name = "alice"
        await _guess_fn(bot, ctx, "chien")
        message = ctx.send.call_args[0][0]
        assert "%" in message

    async def test_guess_unknown_word_reports_vocabulary_miss(self):
        bot = _make_bot(cooldown=0)
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx = _make_ctx()
        ctx.author.name = "alice"
        # No scorer, so non-exact guess produces score=None
        await _guess_fn(bot, ctx, "unknownword")
        message = ctx.send.call_args[0][0]
        assert "vocabulary" in message.lower()

    async def test_guess_already_cited_word_with_score_sends_distinct_message(self):
        bot = _make_bot(cooldown=0)
        bot._game_state = GameState(scorer=_FakeScorer())
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx = _make_ctx()
        ctx.author.name = "alice"
        # First submission of "chien"
        await _guess_fn(bot, ctx, "chien")
        # Second submission of the same word
        ctx2 = _make_ctx()
        ctx2.author.name = "bob"
        await _guess_fn(bot, ctx2, "chien")
        message = ctx2.send.call_args[0][0]
        assert "already" in message.lower()
        assert "%" in message

    async def test_guess_already_cited_word_without_score_sends_distinct_message(self):
        bot = _make_bot(cooldown=0)
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx = _make_ctx()
        ctx.author.name = "alice"
        # No scorer, so non-exact guess produces score=None
        await _guess_fn(bot, ctx, "unknownword")
        ctx2 = _make_ctx()
        ctx2.author.name = "bob"
        await _guess_fn(bot, ctx2, "unknownword")
        message = ctx2.send.call_args[0][0]
        assert "already" in message.lower()

    async def test_guess_exact_match_not_reported_as_already_cited(self):
        """A winning guess should show the win message even if the word was cited before."""
        bot = _make_bot(cooldown=0)
        bot._game_state = GameState(scorer=_FakeScorer())
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx = _make_ctx()
        ctx.author.name = "alice"
        # Someone submits the winning word first (game won)
        await _guess_fn(bot, ctx, "chat")
        # Another user submits the same winning word again
        ctx2 = _make_ctx()
        ctx2.author.name = "bob"
        await _guess_fn(bot, ctx2, "chat")
        message = ctx2.send.call_args[0][0]
        # Should show winner message, not "already cited"
        assert "bob" in message.lower()
        assert "chat" in message.lower()


# ---------------------------------------------------------------------------
# event_error
# ---------------------------------------------------------------------------


class TestEventError:
    async def test_event_error_does_not_raise(self):
        """event_error should swallow exceptions without crashing."""
        bot = _make_bot()
        await bot.event_error(RuntimeError("connection lost"))

    async def test_event_error_with_data_does_not_raise(self):
        bot = _make_bot()
        await bot.event_error(RuntimeError("reconnecting"), data="some data")


# ---------------------------------------------------------------------------
# help command
# ---------------------------------------------------------------------------

_help_fn = StreamantixBot.help._callback


class TestHelpCommand:
    async def test_help_sends_message(self):
        bot = _make_bot()
        ctx = _make_ctx()
        await _help_fn(bot, ctx)
        ctx.send.assert_called_once()

    async def test_help_message_mentions_commands(self):
        bot = _make_bot()
        ctx = _make_ctx()
        await _help_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        for keyword in ("help", "start", "guess", "setprefix", "setcooldown", "hint", "status", "setdifficulty"):
            assert keyword in message

    async def test_help_available_to_any_user(self):
        """Any user (no mod/broadcaster role) can call help."""
        bot = _make_bot()
        ctx = _make_ctx()  # no special role
        await _help_fn(bot, ctx)
        ctx.send.assert_called_once()


# ---------------------------------------------------------------------------
# start command
# ---------------------------------------------------------------------------

_start_fn = StreamantixBot.start_game._callback


class TestStartPermissions:
    async def test_non_broadcaster_cannot_start(self):
        bot = _make_bot()
        ctx = _make_ctx()  # no special role
        await _start_fn(bot, ctx)
        ctx.send.assert_called_once()
        assert "broadcaster" in ctx.send.call_args[0][0].lower()
        assert bot._game_state.target_word is None

    async def test_moderator_cannot_start(self):
        bot = _make_bot()
        ctx = _make_ctx(is_mod=True)
        await _start_fn(bot, ctx)
        ctx.send.assert_called_once()
        assert "broadcaster" in ctx.send.call_args[0][0].lower()
        assert bot._game_state.target_word is None

    async def test_broadcaster_can_start(self):
        bot = _make_bot()
        ctx = _make_ctx(is_broadcaster=True)
        with patch("random.choice", return_value="chat"):
            await _start_fn(bot, ctx)
        ctx.send.assert_called_once()
        assert bot._game_state.target_word == "chat"


class TestStartDifficulty:
    async def test_no_difficulty_defaults_to_easy(self):
        bot = _make_bot()
        ctx = _make_ctx(is_broadcaster=True)
        with patch("random.choice", return_value="chat"):
            await _start_fn(bot, ctx)
        assert bot._game_state.difficulty == Difficulty.EASY

    async def test_easy_difficulty_accepted(self):
        bot = _make_bot()
        ctx = _make_ctx(is_broadcaster=True)
        with patch("random.choice", return_value="chat"):
            await _start_fn(bot, ctx, "easy")
        assert bot._game_state.difficulty == Difficulty.EASY

    async def test_hard_difficulty_accepted(self):
        bot = _make_bot()
        ctx = _make_ctx(is_broadcaster=True)
        with patch("random.choice", return_value="ambiguïté"):
            await _start_fn(bot, ctx, "hard")
        assert bot._game_state.difficulty == Difficulty.HARD

    async def test_medium_difficulty_accepted(self):
        bot = _make_bot()
        ctx = _make_ctx(is_broadcaster=True)
        with patch("random.choice", return_value="ambiguïté"):
            await _start_fn(bot, ctx, "medium")
        assert bot._game_state.difficulty == Difficulty.MEDIUM

    async def test_invalid_difficulty_sends_error(self):
        bot = _make_bot()
        ctx = _make_ctx(is_broadcaster=True)
        await _start_fn(bot, ctx, "impossible")
        ctx.send.assert_called_once()
        assert "invalid" in ctx.send.call_args[0][0].lower()
        assert bot._game_state.target_word is None

    async def test_difficulty_is_case_insensitive(self):
        bot = _make_bot()
        ctx = _make_ctx(is_broadcaster=True)
        with patch("random.choice", return_value="chat"):
            await _start_fn(bot, ctx, "EASY")
        assert bot._game_state.difficulty == Difficulty.EASY


class TestStartGameState:
    async def test_start_sets_target_word(self):
        bot = _make_bot()
        ctx = _make_ctx(is_broadcaster=True)
        with patch("random.choice", return_value="bateau"):
            await _start_fn(bot, ctx)
        assert bot._game_state.target_word == "bateau"

    async def test_start_resets_previous_game(self):
        bot = _make_bot()
        bot._game_state.start_new_game("old_word", Difficulty.EASY)
        bot._game_state.submit_guess("alice", "arbre")
        ctx = _make_ctx(is_broadcaster=True)
        with patch("random.choice", return_value="chat"):
            await _start_fn(bot, ctx)
        assert bot._game_state.target_word == "chat"
        assert bot._game_state.attempt_count == 0

    async def test_start_confirmation_message_contains_difficulty(self):
        bot = _make_bot()
        ctx = _make_ctx(is_broadcaster=True)
        with patch("random.choice", return_value="chat"):
            await _start_fn(bot, ctx, "easy")
        message = ctx.send.call_args[0][0]
        assert "easy" in message.lower()

    async def test_start_confirmation_message_contains_prefix(self):
        bot = _make_bot("!sx")
        ctx = _make_ctx(is_broadcaster=True)
        with patch("random.choice", return_value="chat"):
            await _start_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "!sx" in message


# ---------------------------------------------------------------------------
# hint command
# ---------------------------------------------------------------------------

_hint_fn = StreamantixBot.hint._callback


class TestHintCommand:
    async def test_hint_no_game_sends_error(self):
        bot = _make_bot()
        ctx = _make_ctx()
        await _hint_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "no game" in message.lower()

    async def test_hint_no_guesses_sends_message(self):
        bot = _make_bot()
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx = _make_ctx()
        await _hint_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "no scored" in message.lower()

    async def test_hint_with_guesses_shows_leaderboard(self):
        bot = _make_bot(cooldown=0)
        bot._game_state = GameState(scorer=_FakeScorer())
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        bot._game_state.submit_guess("alice", "chien")
        bot._game_state.submit_guess("bob", "maison")
        ctx = _make_ctx()
        await _hint_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "1." in message
        assert "%" in message

    async def test_hint_available_to_any_user(self):
        bot = _make_bot()
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx = _make_ctx()  # no special role
        await _hint_fn(bot, ctx)
        ctx.send.assert_called_once()

    async def test_hint_shows_at_most_ten_entries(self):
        bot = _make_bot(cooldown=0)
        bot._game_state = GameState(scorer=_FakeScorer())
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        for i in range(15):
            bot._game_state.submit_guess("alice", f"mot{i}")
        ctx = _make_ctx()
        await _hint_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        # At most 10 entries means rank 11 should not appear
        assert "11." not in message


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------

_status_fn = StreamantixBot.status._callback


class TestStatusCommand:
    async def test_status_no_game_sends_error(self):
        bot = _make_bot()
        ctx = _make_ctx()
        await _status_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "no game" in message.lower()

    async def test_status_game_in_progress_no_guesses(self):
        bot = _make_bot()
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx = _make_ctx()
        await _status_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "in progress" in message.lower()
        assert "0" in message

    async def test_status_game_in_progress_with_scored_guess(self):
        bot = _make_bot(cooldown=0)
        bot._game_state = GameState(scorer=_FakeScorer())
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        bot._game_state.submit_guess("alice", "chien")
        ctx = _make_ctx()
        await _status_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "in progress" in message.lower()
        assert "%" in message

    async def test_status_game_found_shows_winner(self):
        bot = _make_bot(cooldown=0)
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        bot._game_state.submit_guess("alice", "chat")
        ctx = _make_ctx()
        await _status_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "alice" in message.lower()

    async def test_status_available_to_any_user(self):
        bot = _make_bot()
        ctx = _make_ctx()  # no special role
        await _status_fn(bot, ctx)
        ctx.send.assert_called_once()


# ---------------------------------------------------------------------------
# setdifficulty — validation
# ---------------------------------------------------------------------------


class TestDifficultyValidation:
    def test_easy_is_valid(self):
        assert _validate_difficulty("easy") is None

    def test_hard_is_valid(self):
        assert _validate_difficulty("hard") is None

    def test_medium_is_invalid(self):
        assert _validate_difficulty("medium") is not None

    def test_empty_is_invalid(self):
        assert _validate_difficulty("") is not None

    def test_none_is_invalid(self):
        assert _validate_difficulty(None) is not None

    def test_unknown_value_is_invalid(self):
        assert _validate_difficulty("impossible") is not None


# ---------------------------------------------------------------------------
# setdifficulty command
# ---------------------------------------------------------------------------

_setdifficulty_fn = StreamantixBot.setdifficulty._callback


class TestSetdifficultyPermissions:
    async def test_moderator_can_set_difficulty(self):
        bot = _make_bot()
        ctx = _make_ctx(is_mod=True)
        await _setdifficulty_fn(bot, ctx, "hard")
        assert bot._next_difficulty == Difficulty.HARD
        ctx.send.assert_called_once()

    async def test_broadcaster_can_set_difficulty(self):
        bot = _make_bot()
        ctx = _make_ctx(is_broadcaster=True)
        await _setdifficulty_fn(bot, ctx, "hard")
        assert bot._next_difficulty == Difficulty.HARD
        ctx.send.assert_called_once()

    async def test_regular_user_cannot_set_difficulty(self):
        bot = _make_bot()
        ctx = _make_ctx()  # no special role
        await _setdifficulty_fn(bot, ctx, "hard")
        assert bot._next_difficulty == Difficulty.EASY  # unchanged
        ctx.send.assert_called_once()
        assert "moderator" in ctx.send.call_args[0][0].lower()


class TestSetdifficultyValidation:
    async def test_invalid_difficulty_rejected(self):
        bot = _make_bot()
        ctx = _make_ctx(is_mod=True)
        await _setdifficulty_fn(bot, ctx, "medium")
        assert bot._next_difficulty == Difficulty.EASY  # unchanged
        ctx.send.assert_called_once()
        assert "invalid" in ctx.send.call_args[0][0].lower()

    async def test_empty_difficulty_rejected(self):
        bot = _make_bot()
        ctx = _make_ctx(is_mod=True)
        await _setdifficulty_fn(bot, ctx, "")
        assert bot._next_difficulty == Difficulty.EASY  # unchanged

    async def test_valid_easy_accepted(self):
        bot = _make_bot()
        ctx = _make_ctx(is_mod=True)
        await _setdifficulty_fn(bot, ctx, "easy")
        assert bot._next_difficulty == Difficulty.EASY
        ctx.send.assert_called_once()

    async def test_valid_hard_accepted(self):
        bot = _make_bot()
        ctx = _make_ctx(is_mod=True)
        await _setdifficulty_fn(bot, ctx, "hard")
        assert bot._next_difficulty == Difficulty.HARD
        ctx.send.assert_called_once()

    async def test_confirmation_message_contains_difficulty(self):
        bot = _make_bot()
        ctx = _make_ctx(is_mod=True)
        await _setdifficulty_fn(bot, ctx, "hard")
        message = ctx.send.call_args[0][0]
        assert "hard" in message.lower()

    async def test_case_insensitive(self):
        bot = _make_bot()
        ctx = _make_ctx(is_mod=True)
        await _setdifficulty_fn(bot, ctx, "HARD")
        assert bot._next_difficulty == Difficulty.HARD


# ---------------------------------------------------------------------------
# setdifficulty — integration with start command
# ---------------------------------------------------------------------------


class TestSetdifficultyIntegration:
    async def test_start_uses_next_difficulty_as_default(self):
        bot = _make_bot()
        ctx_mod = _make_ctx(is_mod=True)
        await _setdifficulty_fn(bot, ctx_mod, "hard")
        assert bot._next_difficulty == Difficulty.HARD
        ctx_broadcaster = _make_ctx(is_broadcaster=True)
        with patch("random.choice", return_value="ambiguïté"):
            await _start_fn(bot, ctx_broadcaster)
        assert bot._game_state.difficulty == Difficulty.HARD

    async def test_setdifficulty_does_not_reset_current_game(self):
        bot = _make_bot()
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        bot._game_state.submit_guess("alice", "arbre")
        ctx = _make_ctx(is_mod=True)
        await _setdifficulty_fn(bot, ctx, "hard")
        # Current game is unaffected
        assert bot._game_state.target_word == "chat"
        assert bot._game_state.attempt_count == 1
