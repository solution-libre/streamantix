"""Tests for game.engine (SemanticEngine and GameEngine)."""

import numpy as np
import pytest
from gensim.models import KeyedVectors

from game.engine import GameEngine, SemanticEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_engine() -> SemanticEngine:
    """Return a SemanticEngine backed by a small in-memory KeyedVectors."""
    kv = KeyedVectors(vector_size=4)
    words = ["chat", "chien", "maison", "voiture"]
    # Use predictable vectors: chat/chien are close, maison/voiture are close,
    # the two pairs are far apart.
    vectors = np.array(
        [
            [1.0, 0.0, 0.0, 0.0],  # chat
            [0.9, 0.1, 0.0, 0.0],  # chien  (close to chat)
            [0.0, 0.0, 1.0, 0.0],  # maison (unrelated to chat)
            [0.0, 0.0, 0.9, 0.1],  # voiture (close to maison)
        ],
        dtype=np.float32,
    )
    kv.add_vectors(words, vectors)

    engine = SemanticEngine.__new__(SemanticEngine)
    engine._model_path = "<in-memory>"
    engine._model = kv
    engine._cleaned_key_map = {w: w for w in words}
    engine._vocab_size = len(kv.key_to_index)  # 4
    return engine


# ---------------------------------------------------------------------------
# SemanticEngine – loading
# ---------------------------------------------------------------------------

class TestSemanticEngineLoading:
    def test_not_loaded_before_load(self):
        engine = SemanticEngine(model_path="/nonexistent/path.bin")
        assert not engine.is_loaded

    def test_is_loaded_after_injecting_model(self):
        engine = _make_engine()
        assert engine.is_loaded

    def test_similarity_raises_when_not_loaded(self):
        engine = SemanticEngine(model_path="/nonexistent/path.bin")
        with pytest.raises(RuntimeError, match="not loaded"):
            engine.similarity("chat", "chien")

    def test_score_guess_raises_when_not_loaded(self):
        engine = SemanticEngine(model_path="/nonexistent/path.bin")
        with pytest.raises(RuntimeError, match="not loaded"):
            engine.score_guess("chat", "chien")


# ---------------------------------------------------------------------------
# SemanticEngine – similarity
# ---------------------------------------------------------------------------

class TestSemanticEngineSimilarity:
    def test_exact_match_returns_one(self):
        engine = _make_engine()
        assert engine.score_guess("chat", "chat") == 1.0

    def test_similar_words_return_high_score(self):
        engine = _make_engine()
        score = engine.score_guess("chien", "chat")
        assert score is not None
        assert score > 0.5

    def test_unrelated_words_return_low_score(self):
        engine = _make_engine()
        score = engine.score_guess("maison", "chat")
        assert score is not None
        assert score < 0.5

    def test_score_is_between_zero_and_one(self):
        engine = _make_engine()
        for guess in ["chat", "chien", "maison", "voiture"]:
            score = engine.score_guess(guess, "chat")
            assert score is not None
            assert 0.0 <= score <= 1.0

    def test_score_is_log_rank(self):
        """score_guess returns a logarithmic rank score, not raw cosine similarity.

        With vocab_size=4 and the log formula, chien (rank 1) scores
        1 - log(2)/log(5) ≈ 0.57 and maison (rank 2) scores
        1 - log(3)/log(5) ≈ 0.32, so chien must outrank maison.
        """
        engine = _make_engine()
        score_chien = engine.score_guess("chien", "chat")   # rank 1 → ~0.57
        score_maison = engine.score_guess("maison", "chat") # rank 2 → ~0.32
        assert score_chien is not None
        assert score_maison is not None
        assert score_chien > score_maison

    def test_all_vocab_words_score_above_zero(self):
        """Every in-vocabulary word scores strictly > 0."""
        engine = _make_engine()
        for word in ["chien", "maison", "voiture"]:
            score = engine.score_guess(word, "chat")
            assert score is not None
            assert score > 0.0, f"{word!r} scored 0"

    def test_unknown_word_returns_none(self):
        engine = _make_engine()
        assert engine.score_guess("inconnu", "chat") is None

    def test_similarity_unknown_word_returns_none(self):
        engine = _make_engine()
        assert engine.similarity("inconnu", "chat") is None
        assert engine.similarity("chat", "inconnu") is None

    def test_similarity_is_symmetric(self):
        engine = _make_engine()
        assert engine.similarity("chat", "chien") == pytest.approx(
            engine.similarity("chien", "chat"), abs=1e-6
        )


# ---------------------------------------------------------------------------
# GameEngine – initialisation
# ---------------------------------------------------------------------------

class TestGameEngineInit:
    def test_target_word_stored(self):
        ge = GameEngine("chat")
        assert ge.target_word == "chat"

    def test_initial_guesses_empty(self):
        ge = GameEngine("chat")
        assert ge._guesses == {}


# ---------------------------------------------------------------------------
# GameEngine – score_guess
# ---------------------------------------------------------------------------

class TestScoreGuess:
    def test_exact_match_returns_one(self):
        ge = GameEngine("chat", semantic_engine=_make_engine())
        assert ge.score_guess("chat") == 1.0

    def test_unrelated_word_returns_low_score(self):
        ge = GameEngine("chat", semantic_engine=_make_engine())
        score = ge.score_guess("maison")
        assert score < 0.5

    def test_score_is_between_zero_and_one(self):
        ge = GameEngine("chat", semantic_engine=_make_engine())
        for word in ["chat", "chien", "maison"]:
            assert 0.0 <= ge.score_guess(word) <= 1.0

    def test_fallback_exact_match_without_engine(self):
        """Without a semantic engine, only exact matches score 1.0."""
        ge = GameEngine("chat")
        assert ge.score_guess("chat") == 1.0
        assert ge.score_guess("chien") == 0.0

    def test_unknown_word_falls_back_to_zero(self):
        """Unknown words should fall back to 0 rather than raise."""
        ge = GameEngine("chat", semantic_engine=_make_engine())
        assert ge.score_guess("motinconnu") == 0.0


# ---------------------------------------------------------------------------
# GameEngine – register_guess
# ---------------------------------------------------------------------------

class TestRegisterGuess:
    def test_register_guess_records_score(self):
        ge = GameEngine("chat", semantic_engine=_make_engine())
        score = ge.register_guess("alice", "chien")
        assert ge._guesses["alice"] == score

    def test_register_guess_keeps_best_score(self):
        ge = GameEngine("chat", semantic_engine=_make_engine())
        ge.register_guess("alice", "maison")  # low score
        ge.register_guess("alice", "chien")   # higher score
        assert ge._guesses["alice"] >= ge.score_guess("maison")
