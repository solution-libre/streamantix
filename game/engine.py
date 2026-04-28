"""Game engine: state management and guess scoring."""

import math
import os
import pathlib

from gensim.models import KeyedVectors

from game.word_utils import build_cleaned_key_map, clean_word

_DEFAULT_MODEL_PATH = os.getenv(
    "MODEL_PATH", "models/frWac_no_postag_no_phrase_700_skip_cut50.bin"
)
_DEFAULT_TOP_N: int = int(os.getenv("SCORING_TOP_N", "100000"))


class SemanticEngine:
    """Word-embedding-based similarity engine.

    Loads a Word2Vec :class:`~gensim.models.KeyedVectors` model and exposes
    helpers for comparing words semantically.

    Args:
        model_path: Path to the binary ``.bin`` Word2Vec file.  Defaults to
            the value of the ``MODEL_PATH`` environment variable, or the
            standard ``models/frWac_no_postag_no_phrase_700_skip_cut50.bin``
            path when the variable is unset.
        top_n: Number of nearest neighbours used for rank scoring.  Words
            ranked beyond this threshold return ``0.0``.  Defaults to the
            value of the ``SCORING_TOP_N`` environment variable, or ``1000``
            when unset.
    """

    def __init__(self, model_path: str | pathlib.Path | None = None, top_n: int = _DEFAULT_TOP_N) -> None:
        if top_n <= 0:
            raise ValueError(f"top_n must be a positive integer, got {top_n}")
        self._model_path = str(model_path or _DEFAULT_MODEL_PATH)
        self._model: KeyedVectors | None = None
        self._cleaned_key_map: dict[str, str] = {}
        self._top_n: int = top_n

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load the Word2Vec model from disk.

        After loading, a cleaned-key map is built so that user-supplied words
        can be looked up regardless of POS-tag suffixes in the vocabulary.
        """
        self._model = KeyedVectors.load_word2vec_format(
            self._model_path, binary=True, unicode_errors="ignore"
        )
        self._cleaned_key_map = build_cleaned_key_map(self._model.key_to_index)

    @property
    def is_loaded(self) -> bool:
        """Return ``True`` if the model has been loaded."""
        return self._model is not None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def similarity(self, word_a: str, word_b: str) -> float | None:
        """Return the cosine similarity between two words.

        Both words are cleaned/normalised before lookup.  If either word is
        absent from the model vocabulary, ``None`` is returned.

        Args:
            word_a: First word.
            word_b: Second word.

        Returns:
            A float in ``[-1, 1]`` (typically ``[0, 1]`` for French nouns), or
            ``None`` if one of the words is unknown.
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")
        key_a = self._cleaned_key_map.get(clean_word(word_a))
        key_b = self._cleaned_key_map.get(clean_word(word_b))
        if key_a is None or key_b is None:
            return None
        return float(self._model.similarity(key_a, key_b))

    def score_guess(self, guess: str, target: str) -> float | None:
        """Score a player's guess against the target word.

        Returns ``1.0`` for an exact (cleaned) match, or a **top-N rank
        score** in ``[0, 1)`` for a non-exact guess.  Returns ``None`` when
        either word is missing from the vocabulary.

        The score is computed over the top-``top_n`` nearest neighbours of
        *target*: a score of ``0.99`` means the guess is among the top 1 %
        of the nearest words.  Words ranked beyond ``top_n`` return ``0.0``.

        Args:
            guess: The word submitted by the player.
            target: The secret target word.

        Returns:
            A float in ``[0, 1]``, or ``None``.
        """
        if clean_word(guess) == clean_word(target):
            return 1.0
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")
        key_guess = self._cleaned_key_map.get(clean_word(guess))
        key_target = self._cleaned_key_map.get(clean_word(target))
        if key_guess is None or key_target is None:
            return None
        rank = self._model.rank(key_target, key_guess)
        if rank > self._top_n:
            return 0.0
        return max(0.0, 1.0 - math.log(rank + 1) / math.log(self._top_n + 1))


class GameEngine:
    """Manage the game state for a single channel.

    Attributes:
        target_word: The secret word players are trying to guess.
    """

    def __init__(self, target_word: str, semantic_engine: SemanticEngine | None = None) -> None:
        self.target_word = target_word
        self._guesses: dict[str, float] = {}
        self._semantic: SemanticEngine | None = semantic_engine

    def score_guess(self, word: str) -> float:
        """Return a similarity score between *word* and the target word.

        Returns a float in [0, 1] where 1 means an exact match.
        Uses the semantic engine when available; falls back to exact-match
        only when no engine is configured.
        """
        if self._semantic is not None:
            result = self._semantic.score_guess(word, self.target_word)
            if result is not None:
                return result
        if word == self.target_word:
            return 1.0
        return 0.0

    def register_guess(self, user: str, word: str) -> float:
        """Record a guess from *user* and return its score."""
        score = self.score_guess(word)
        self._guesses[user] = max(self._guesses.get(user, 0.0), score)
        return score
