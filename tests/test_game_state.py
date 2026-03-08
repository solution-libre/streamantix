"""Tests for game state management (game.state.GameState)."""

import pytest

from game.state import Difficulty, GameState, GuessEntry, GuessResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeScorer:
    """Deterministic scorer for testing: returns the length-ratio as score."""

    def score_guess(self, guess: str, target: str) -> float | None:
        if not target:
            return None
        return min(1.0, len(guess) / len(target))


def _make_state(with_scorer: bool = False) -> GameState:
    scorer = _FakeScorer() if with_scorer else None
    return GameState(scorer=scorer)


# ---------------------------------------------------------------------------
# TestGameStateReset
# ---------------------------------------------------------------------------


class TestGameStateReset:
    def test_reset_clears_guesses(self):
        """Resetting the game should clear all recorded guesses."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chien")
        assert gs.attempt_count == 1

        gs.start_new_game("maison", Difficulty.EASY)
        assert gs.attempt_count == 0
        assert gs.history == []

    def test_reset_changes_target_word(self):
        """Resetting the game should allow setting a new target word."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        assert gs.target_word == "chat"

        gs.start_new_game("maison", Difficulty.MEDIUM)
        assert gs.target_word == "maison"
        assert gs.difficulty == Difficulty.MEDIUM

    def test_reset_clears_is_found(self):
        """Resetting after a win should clear the found flag."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chat")
        assert gs.is_found

        gs.start_new_game("maison", Difficulty.EASY)
        assert not gs.is_found


# ---------------------------------------------------------------------------
# TestGameStateWinCondition
# ---------------------------------------------------------------------------


class TestGameStateWinCondition:
    def test_exact_guess_triggers_win(self):
        """A guess that exactly matches the target word should trigger a win."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        result = gs.submit_guess("alice", "chat")
        assert result.is_found
        assert gs.is_found

    def test_wrong_guess_does_not_trigger_win(self):
        """A non-matching guess should not trigger a win."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        result = gs.submit_guess("alice", "chien")
        assert not result.is_found
        assert not gs.is_found

    def test_normalized_guess_triggers_win(self):
        """A guess that matches after normalisation should trigger a win."""
        gs = _make_state()
        gs.start_new_game("Chat", Difficulty.EASY)
        result = gs.submit_guess("alice", "CHAT")
        assert result.is_found
        assert gs.is_found

    def test_found_word_returns_raw_winning_word(self):
        """found_word should return the exact string the winner typed."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "CHAT")
        assert gs.found_word == "CHAT"

    def test_found_word_is_none_before_win(self):
        """found_word should be None until a correct guess is submitted."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        assert gs.found_word is None


# ---------------------------------------------------------------------------
# TestGameStateHistory
# ---------------------------------------------------------------------------


class TestGameStateHistory:
    def test_guess_history_appended(self):
        """Each guess should be appended to the history in order."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chien")
        gs.submit_guess("bob", "maison")
        assert len(gs.history) == 2
        assert gs.history[0].user == "alice"
        assert gs.history[1].user == "bob"

    def test_history_stores_raw_and_normalized_word(self):
        """GuessEntry should carry both the raw and the normalised word."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "CHAT!")
        entry = gs.history[0]
        assert entry.raw_word == "CHAT!"
        assert entry.normalized_word == "chat"

    def test_attempt_count_increments(self):
        """attempt_count should increase by one for each submitted guess."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        assert gs.attempt_count == 0
        gs.submit_guess("alice", "chien")
        assert gs.attempt_count == 1
        gs.submit_guess("bob", "maison")
        assert gs.attempt_count == 2

    def test_submit_guess_raises_without_active_game(self):
        """Submitting a guess before start_new_game should raise RuntimeError."""
        gs = _make_state()
        with pytest.raises(RuntimeError, match="No game in progress"):
            gs.submit_guess("alice", "chat")

    def test_guess_result_contains_entry(self):
        """GuessResult should carry the GuessEntry that was recorded."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        result = gs.submit_guess("alice", "chien")
        assert isinstance(result, GuessResult)
        assert isinstance(result.entry, GuessEntry)
        assert result.entry.user == "alice"


# ---------------------------------------------------------------------------
# TestAlreadyCited
# ---------------------------------------------------------------------------


class TestAlreadyCited:
    def test_first_guess_is_not_already_cited(self):
        """The first submission of a word should not be marked as already cited."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        result = gs.submit_guess("alice", "chien")
        assert not result.already_cited

    def test_repeated_word_is_already_cited(self):
        """A word submitted a second time by any player should be already cited."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chien")
        result = gs.submit_guess("bob", "chien")
        assert result.already_cited

    def test_same_user_repeated_word_is_already_cited(self):
        """A word submitted twice by the same user should be already cited."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chien")
        result = gs.submit_guess("alice", "chien")
        assert result.already_cited

    def test_different_word_is_not_already_cited(self):
        """A word not yet in history should not be marked as already cited."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chien")
        result = gs.submit_guess("bob", "maison")
        assert not result.already_cited

    def test_already_cited_normalised_match(self):
        """Words that normalise to the same form should be detected as already cited."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "Chien")
        result = gs.submit_guess("bob", "CHIEN")
        assert result.already_cited

    def test_already_cited_word_not_appended_to_history(self):
        """Already-cited guesses should not be recorded again in history."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chien")
        gs.submit_guess("bob", "chien")
        assert gs.attempt_count == 1

    def test_already_cited_resets_on_new_game(self):
        """After starting a new game, previously cited words are no longer cited."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chien")
        gs.start_new_game("maison", Difficulty.EASY)
        result = gs.submit_guess("bob", "chien")
        assert not result.already_cited


# ---------------------------------------------------------------------------
# TestGameStateLeaderboard
# ---------------------------------------------------------------------------


class TestGameStateLeaderboard:
    def test_top_guesses_returned_in_order(self):
        """The leaderboard should return guesses sorted by descending score."""
        gs = _make_state(with_scorer=True)
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "ch")        # score = 2/4 = 0.5
        gs.submit_guess("bob", "chat")        # score = 1.0 (exact match / found)
        gs.submit_guess("carol", "c")         # score = 1/4 = 0.25

        top = gs.top_guesses()
        assert top[0].score >= top[1].score >= top[2].score

    def test_leaderboard_empty_at_start(self):
        """The leaderboard should be empty when no guesses have been made."""
        gs = _make_state()
        gs.start_new_game("chat", Difficulty.EASY)
        assert gs.top_guesses() == []

    def test_top_guesses_respects_n(self):
        """top_guesses(n) should return at most n entries."""
        gs = _make_state(with_scorer=True)
        gs.start_new_game("chat", Difficulty.EASY)
        for word in ["a", "ab", "abc", "abcd", "abcde"]:
            gs.submit_guess("alice", word)
        assert len(gs.top_guesses(n=3)) == 3

    def test_already_cited_word_excluded_from_top_guesses(self):
        """A word submitted a second time should not appear twice in the leaderboard."""
        gs = _make_state(with_scorer=True)
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chien")
        gs.submit_guess("bob", "chien")
        top = gs.top_guesses()
        normalized_words = [e.normalized_word for e in top]
        assert normalized_words.count("chien") == 1

    def test_score_stored_in_entry_with_scorer(self):
        """When a scorer is provided, GuessEntry.score should be set."""
        gs = _make_state(with_scorer=True)
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chien")
        assert gs.history[0].score is not None

    def test_score_none_without_scorer_for_non_exact(self):
        """Without a scorer, non-exact guesses should have score=None."""
        gs = _make_state(with_scorer=False)
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chien")
        assert gs.history[0].score is None

    def test_exact_guess_score_is_one_even_without_scorer(self):
        """Exact guesses always score 1.0 regardless of scorer."""
        gs = _make_state(with_scorer=False)
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chat")
        assert gs.history[0].score == 1.0

