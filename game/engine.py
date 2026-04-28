"""Game engine: state management and guess scoring."""

import math
import pathlib

from gensim.models import KeyedVectors

import config
from game.word_utils import build_cleaned_key_map, clean_word

_DEFAULT_MODEL_PATH: str = config.MODEL_PATH


class SemanticEngine:
    """Word-embedding-based similarity engine.

    Loads a Word2Vec :class:`~gensim.models.KeyedVectors` model and exposes
    helpers for comparing words semantically.

    Args:
        model_path: Path to the binary ``.bin`` Word2Vec file.  Defaults to
            the value of the ``MODEL_PATH`` environment variable, or the
            standard ``models/frWac_no_postag_no_phrase_700_skip_cut50.bin``
            path when the variable is unset.
    """

    def __init__(
        self,
        model_path: str | pathlib.Path | None = None,
    ) -> None:
        self._model_path = str(model_path or _DEFAULT_MODEL_PATH)
        self._model: KeyedVectors | None = None
        self._cleaned_key_map: dict[str, str] = {}
        self._vocab_size: int | None = None

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
        self._vocab_size = len(self._model.key_to_index)

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

        Returns ``1.0`` for an exact (cleaned) match, or a **logarithmic rank
        score** in ``(0, 1)`` for a non-exact in-vocabulary guess.  Returns
        ``None`` when either word is missing from the vocabulary.

        The score formula is ``1 − log(rank+1) / log(V+1)`` where *rank* is
        1-based (1 = closest neighbour) and *V* is the full vocabulary size.
        Because rank ≤ V−1 < V for any in-vocabulary word, every valid guess
        returns a strictly positive score.  The closest synonym scores ≈94 %;
        rank 10 000 ≈23 %; the furthest possible word scores ≈0.003 %.

        Args:
            guess: The word submitted by the player.
            target: The secret target word.

        Returns:
            A float in ``(0, 1]``, or ``None`` if either word is OOV.
        """
        clean_guess = clean_word(guess)
        clean_target = clean_word(target)
        if clean_guess == clean_target:
            return 1.0
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")
        key_guess = self._cleaned_key_map.get(clean_guess)
        key_target = self._cleaned_key_map.get(clean_target)
        if key_guess is None or key_target is None:
            return None
        rank = self._model.rank(key_target, key_guess)
        vocab_size = self._vocab_size or len(self._model.key_to_index)
        return max(0.0, 1.0 - math.log(rank + 1) / math.log(vocab_size + 1))


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
