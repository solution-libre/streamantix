"""Functional tests: complete multi-step game scenarios (game layer only, no overlay, no Twitch network)."""

from __future__ import annotations

from unittest.mock import patch

from bot.bot import StreamantixBot
from game.state import Difficulty, GameState
from tests.conftest import FakeScorer, make_bot, make_ctx

_start_fn = StreamantixBot.start_game._callback
_guess_fn = StreamantixBot.guess._callback
_hint_fn = StreamantixBot.hint._callback
_status_fn = StreamantixBot.status._callback
_solution_fn = StreamantixBot.solution._callback
_setdifficulty_fn = StreamantixBot.setdifficulty._callback


# ---------------------------------------------------------------------------
# TestCompleteGameScenario
# ---------------------------------------------------------------------------


class TestCompleteGameScenario:
    async def test_broadcaster_starts_game_and_player_wins(self):
        bot = make_bot(cooldown=0)
        ctx_broadcaster = make_ctx(is_broadcaster=True)
        with patch("bot.bot.load_word_list", return_value=["chat"]):
            await _start_fn(bot, ctx_broadcaster)
        assert bot._game_state.target_word == "chat"

        ctx_player = make_ctx(author_name="alice")
        await _guess_fn(bot, ctx_player, "chat")

        assert bot._game_state.is_found
        message = ctx_player.send.call_args[0][0]
        assert "alice" in message.lower()

    async def test_multiple_players_compete_only_first_wins(self):
        bot = make_bot(cooldown=0)
        bot._game_state.start_new_game("chat", Difficulty.EASY)

        ctx_alice = make_ctx(author_name="alice")
        await _guess_fn(bot, ctx_alice, "chat")
        assert bot._game_state.is_found
        assert bot._game_state.found_by == "alice"

        ctx_bob = make_ctx(author_name="bob")
        await _guess_fn(bot, ctx_bob, "chat")
        message = ctx_bob.send.call_args[0][0]
        assert "alice" in message.lower()
        assert "chat" in message.lower()

    async def test_guess_count_increments_across_players(self):
        bot = make_bot(cooldown=0, scorer=FakeScorer())
        bot._game_state.start_new_game("chat", Difficulty.EASY)

        for name, word in [("alice", "chien"), ("bob", "maison"), ("carol", "arbre")]:
            ctx = make_ctx(author_name=name)
            await _guess_fn(bot, ctx, word)

        assert bot._game_state.attempt_count == 3


# ---------------------------------------------------------------------------
# TestDifficultyFlow
# ---------------------------------------------------------------------------


class TestDifficultyFlow:
    async def test_setdifficulty_affects_next_game(self):
        bot = make_bot()
        ctx_mod = make_ctx(is_mod=True)
        await _setdifficulty_fn(bot, ctx_mod, "hard")
        assert bot._next_difficulty == Difficulty.HARD

        ctx_broadcaster = make_ctx(is_broadcaster=True)
        with patch("bot.bot.load_word_list", return_value=["ambiguïté"]):
            await _start_fn(bot, ctx_broadcaster)
        assert bot._game_state.difficulty == Difficulty.HARD

    async def test_start_with_explicit_difficulty_overrides_next_difficulty(self):
        bot = make_bot()
        ctx_mod = make_ctx(is_mod=True)
        await _setdifficulty_fn(bot, ctx_mod, "hard")
        assert bot._next_difficulty == Difficulty.HARD

        ctx_broadcaster = make_ctx(is_broadcaster=True)
        with patch("bot.bot.load_word_list", return_value=["chat"]):
            await _start_fn(bot, ctx_broadcaster, "easy")
        assert bot._game_state.difficulty == Difficulty.EASY
        # _next_difficulty should remain hard (not overwritten by explicit start arg)
        assert bot._next_difficulty == Difficulty.HARD

    async def test_invalid_difficulty_sends_error(self):
        bot = make_bot()
        ctx_broadcaster = make_ctx(is_broadcaster=True)
        await _start_fn(bot, ctx_broadcaster, "invalid")
        message = ctx_broadcaster.send.call_args[0][0]
        assert "invalid" in message.lower()
        assert bot._game_state.target_word is None


# ---------------------------------------------------------------------------
# TestHintAndStatus
# ---------------------------------------------------------------------------


class TestHintAndStatus:
    async def test_hint_shows_sorted_leaderboard(self):
        bot = make_bot(scorer=FakeScorer())
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        # Scores: c=1/4=0.25, ch=2/4=0.5, cha=3/4=0.75 (FakeScorer length-ratio)
        for user, word in [("alice", "c"), ("bob", "ch"), ("carol", "cha")]:
            bot._game_state.submit_guess(user, word)

        ctx = make_ctx()
        await _hint_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        # All three words must appear in the message
        assert "c" in message
        assert "ch" in message
        assert "cha" in message
        # "1." must appear (top rank marker)
        assert "1." in message

    async def test_status_shows_attempt_count(self):
        bot = make_bot(cooldown=0, scorer=FakeScorer())
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        for name, word in [("alice", "chien"), ("bob", "maison")]:
            ctx_g = make_ctx(author_name=name)
            await _guess_fn(bot, ctx_g, word)

        ctx = make_ctx()
        await _status_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "2" in message

    async def test_status_reports_no_game_when_inactive(self):
        bot = make_bot()
        ctx = make_ctx()
        await _status_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "no game" in message.lower()

    async def test_hint_reports_no_guesses_when_empty(self):
        bot = make_bot()
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx = make_ctx()
        await _hint_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "no scored" in message.lower()


# ---------------------------------------------------------------------------
# TestSolutionCommand
# ---------------------------------------------------------------------------


class TestSolutionCommand:
    async def test_solution_reveals_word_and_marks_found(self):
        bot = make_bot(cooldown=0)
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx = make_ctx(is_broadcaster=True, author_name="broadcaster")
        await _solution_fn(bot, ctx)
        assert bot._game_state.is_found
        message = ctx.send.call_args[0][0]
        assert "chat" in message.lower()

    async def test_solution_requires_broadcaster(self):
        bot = make_bot()
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx = make_ctx(author_name="viewer")
        await _solution_fn(bot, ctx)
        assert not bot._game_state.is_found
        message = ctx.send.call_args[0][0]
        assert "broadcaster" in message.lower()

    async def test_solution_fails_without_active_game(self):
        bot = make_bot()
        ctx = make_ctx(is_broadcaster=True)
        await _solution_fn(bot, ctx)
        message = ctx.send.call_args[0][0]
        assert "no game" in message.lower()


# ---------------------------------------------------------------------------
# TestGuessEdgeCases
# ---------------------------------------------------------------------------


class TestGuessEdgeCases:
    async def test_duplicate_guess_gets_already_cited_response(self):
        bot = make_bot(cooldown=0)
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx1 = make_ctx(author_name="alice")
        await _guess_fn(bot, ctx1, "chien")
        ctx2 = make_ctx(author_name="bob")
        await _guess_fn(bot, ctx2, "chien")
        message = ctx2.send.call_args[0][0]
        assert "already" in message.lower()

    async def test_invalid_word_characters_rejected(self):
        bot = make_bot(cooldown=0)
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx = make_ctx(author_name="alice")
        await _guess_fn(bot, ctx, "mot123")
        message = ctx.send.call_args[0][0]
        assert "letter" in message.lower()

    async def test_word_too_long_rejected(self):
        bot = make_bot(cooldown=0)
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx = make_ctx(author_name="alice")
        await _guess_fn(bot, ctx, "a" * 51)
        message = ctx.send.call_args[0][0]
        assert "long" in message.lower() or "max" in message.lower()

    async def test_cooldown_blocks_rapid_fire_guesses(self):
        bot = make_bot(cooldown=30, scorer=FakeScorer())
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        ctx1 = make_ctx(author_name="alice")
        await _guess_fn(bot, ctx1, "chien")
        # Second guess from the same user while on cooldown
        ctx2 = make_ctx(author_name="alice")
        await _guess_fn(bot, ctx2, "maison")
        message = ctx2.send.call_args[0][0]
        assert "wait" in message.lower()
