"""Serialise :class:`~game.state.GameState` for the overlay WebSocket feed."""

from __future__ import annotations

from game.state import GameState


def serialize_game_state(gs: GameState) -> dict:
    """Return a JSON-serialisable snapshot of *gs* for the overlay.

    The returned dict contains:

    * ``status`` – ``"idle"``, ``"running"``, or ``"found"``.
    * ``difficulty`` – current difficulty value, or ``None``.
    * ``attempt_count`` – total guesses submitted.
    * ``best_guess`` – ``{"word": …, "score": …}`` for the highest-scored
      entry, or ``None``.
    * ``last_guess`` – ``{"word": …, "user": …, "score": …}`` for the most
      recent entry, or ``None``.
    * ``top_guesses`` – list of up to 10 entries ordered by descending score.
    * ``target_word`` – the secret word, exposed only after the game is won.

    Args:
        gs: The :class:`~game.state.GameState` instance to serialise.

    Returns:
        A plain ``dict`` suitable for ``json.dumps``.
    """
    if gs.target_word is None:
        status = "idle"
    elif gs.is_found:
        status = "found"
    else:
        status = "running"

    top = gs.top_guesses(10)
    best = top[0] if top else None
    history = gs.history
    last = history[-1] if history else None

    return {
        "status": status,
        "difficulty": gs.difficulty.value if gs.difficulty is not None else None,
        "attempt_count": gs.attempt_count,
        "best_guess": (
            {"word": best.raw_word, "score": best.score}
            if best is not None
            else None
        ),
        "last_guess": (
            {"word": last.raw_word, "user": last.user, "score": last.score}
            if last is not None
            else None
        ),
        "top_guesses": [
            {"word": e.raw_word, "score": e.score, "user": e.user}
            for e in top
        ],
        "target_word": gs.target_word if gs.is_found else None,
    }
