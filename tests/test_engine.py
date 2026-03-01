"""Skeleton tests for game.engine (GameEngine)."""

import pytest

from game.engine import GameEngine


class TestGameEngineInit:
    @pytest.mark.skip(reason="not implemented")
    def test_target_word_stored(self):
        """GameEngine should store the target word on initialization."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="not implemented")
    def test_initial_guesses_empty(self):
        """GameEngine should start with no recorded guesses."""
        assert False, "not implemented"


class TestScoreGuess:
    @pytest.mark.skip(reason="semantic scoring not implemented")
    def test_exact_match_returns_one(self):
        """An exact match should return a score of 1.0."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="semantic scoring not implemented")
    def test_unrelated_word_returns_low_score(self):
        """An unrelated word should return a score close to 0."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="semantic scoring not implemented")
    def test_score_is_between_zero_and_one(self):
        """Score must always be in the range [0, 1]."""
        assert False, "not implemented"


class TestRegisterGuess:
    @pytest.mark.skip(reason="not implemented")
    def test_register_guess_records_score(self):
        """register_guess should record the score for the given user."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="not implemented")
    def test_register_guess_keeps_best_score(self):
        """Subsequent guesses should keep the user's best score."""
        assert False, "not implemented"
