"""Game engine: state management and guess scoring."""


class GameEngine:
    """Manage the game state for a single channel.

    Attributes:
        target_word: The secret word players are trying to guess.
    """

    def __init__(self, target_word: str) -> None:
        self.target_word = target_word
        self._guesses: dict[str, float] = {}

    def score_guess(self, word: str) -> float:
        """Return a similarity score between *word* and the target word.

        Returns a float in [0, 1] where 1 means an exact match.
        This is a stub – replace with gensim-based scoring.
        """
        # TODO: implement semantic similarity using a loaded gensim model
        if word == self.target_word:
            return 1.0
        return 0.0

    def register_guess(self, user: str, word: str) -> float:
        """Record a guess from *user* and return its score."""
        score = self.score_guess(word)
        self._guesses[user] = max(self._guesses.get(user, 0.0), score)
        return score
