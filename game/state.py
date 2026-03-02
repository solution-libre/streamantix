"""Game state management: target word, guess history, win detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol

from game.word_utils import clean_word


class Difficulty(str, Enum):
    """Difficulty level for a game round."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Scorer(Protocol):
    """Protocol for semantic scoring back-ends.

    Allows injecting a fake scorer in tests without loading large models.
    """

    def score_guess(self, guess: str, target: str) -> float | None:
        """Return a similarity score in ``[0, 1]``, or ``None`` if unknown."""
        ...


@dataclass
class GuessEntry:
    """A single guess submitted during a game round.

    Attributes:
        user: Twitch login of the player who submitted the guess.
        raw_word: The word exactly as typed by the player.
        normalized_word: The result of :func:`~game.word_utils.clean_word`.
        score: Similarity score in ``[0, 1]``, or ``None`` when unavailable.
        timestamp: UTC time at which the guess was recorded.
    """

    user: str
    raw_word: str
    normalized_word: str
    score: float | None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GuessResult:
    """Outcome of a single :meth:`GameState.submit_guess` call.

    Attributes:
        entry: The :class:`GuessEntry` that was recorded.
        is_found: ``True`` if this guess matched the target word.
    """

    entry: GuessEntry
    is_found: bool


class GameState:
    """Manage the state of a single Streamantix game round.

    Supports dependency injection of a :class:`Scorer` so that tests can
    provide a lightweight fake without loading a Word2Vec model.

    Args:
        scorer: Optional semantic scorer.  When provided, each guess is scored
            for similarity against the target word.
    """

    def __init__(self, scorer: Scorer | None = None) -> None:
        self._scorer = scorer
        self._target_word: str | None = None
        self._difficulty: Difficulty | None = None
        self._history: list[GuessEntry] = []
        self._is_found: bool = False

    # ------------------------------------------------------------------
    # Game lifecycle
    # ------------------------------------------------------------------

    def start_new_game(self, target_word: str, difficulty: Difficulty) -> None:
        """Reset state and begin a new round with *target_word*.

        Args:
            target_word: The secret word players must guess.
            difficulty: Difficulty level for the round.
        """
        self._target_word = target_word
        self._difficulty = difficulty
        self._history = []
        self._is_found = False

    # ------------------------------------------------------------------
    # Guessing
    # ------------------------------------------------------------------

    def submit_guess(self, user: str, word: str) -> GuessResult:
        """Record a guess from *user* and return the outcome.

        Args:
            user: Twitch login of the guessing player.
            word: The raw word submitted by the player.

        Returns:
            A :class:`GuessResult` with the recorded entry and win flag.

        Raises:
            RuntimeError: If no game is currently in progress.
        """
        if self._target_word is None:
            raise RuntimeError("No game in progress. Call start_new_game() first.")

        normalized = clean_word(word)
        target_normalized = clean_word(self._target_word)

        found = normalized == target_normalized

        score: float | None
        if found:
            score = 1.0
        elif self._scorer is not None:
            score = self._scorer.score_guess(word, self._target_word)
        else:
            score = None

        entry = GuessEntry(
            user=user,
            raw_word=word,
            normalized_word=normalized,
            score=score,
        )
        self._history.append(entry)

        if found:
            self._is_found = True

        return GuessResult(entry=entry, is_found=found)

    # ------------------------------------------------------------------
    # State inspection
    # ------------------------------------------------------------------

    @property
    def target_word(self) -> str | None:
        """The current target word, or ``None`` if no game is in progress."""
        return self._target_word

    @property
    def difficulty(self) -> Difficulty | None:
        """The difficulty of the current round, or ``None`` if not started."""
        return self._difficulty

    @property
    def is_found(self) -> bool:
        """``True`` once a player has guessed the target word."""
        return self._is_found

    @property
    def found_word(self) -> str | None:
        """The raw word that won the game, or ``None`` if not yet found."""
        if not self._is_found or self._target_word is None:
            return None
        target_normalized = clean_word(self._target_word)
        for entry in reversed(self._history):
            if entry.normalized_word == target_normalized:
                return entry.raw_word
        return None  # pragma: no cover

    @property
    def attempt_count(self) -> int:
        """Total number of guesses submitted in the current round."""
        return len(self._history)

    @property
    def history(self) -> list[GuessEntry]:
        """Read-only snapshot of all guess entries in submission order."""
        return list(self._history)

    def top_guesses(self, n: int = 10) -> list[GuessEntry]:
        """Return the top *n* guesses by score, highest first.

        Only entries that have a score are included.

        Args:
            n: Maximum number of entries to return.

        Returns:
            A list of at most *n* :class:`GuessEntry` objects.
        """
        scored = [e for e in self._history if e.score is not None]
        return sorted(scored, key=lambda e: e.score or 0.0, reverse=True)[:n]
