"""Skeleton tests for game state management (game.engine.GameEngine)."""

import pytest

from game.engine import GameEngine


class TestGameStateReset:
    @pytest.mark.skip(reason="reset not implemented")
    def test_reset_clears_guesses(self):
        """Resetting the game should clear all recorded guesses."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="reset not implemented")
    def test_reset_changes_target_word(self):
        """Resetting the game should allow setting a new target word."""
        assert False, "not implemented"


class TestGameStateWinCondition:
    @pytest.mark.skip(reason="win condition not implemented")
    def test_exact_guess_triggers_win(self):
        """A guess that exactly matches the target word should trigger a win."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="win condition not implemented")
    def test_wrong_guess_does_not_trigger_win(self):
        """A non-matching guess should not trigger a win."""
        assert False, "not implemented"


class TestGameStateLeaderboard:
    @pytest.mark.skip(reason="leaderboard not implemented")
    def test_top_guesses_returned_in_order(self):
        """The leaderboard should return guesses sorted by descending score."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="leaderboard not implemented")
    def test_leaderboard_empty_at_start(self):
        """The leaderboard should be empty when no guesses have been made."""
        assert False, "not implemented"
