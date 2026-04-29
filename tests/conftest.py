"""Shared pytest fixtures and helpers for all Streamantix tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.bot import StreamantixBot
from bot.cooldown import CooldownManager
from game.state import Difficulty, GameState


class FakeScorer:
    """Deterministic scorer: returns min(1.0, len(guess)/len(target))."""

    def score_guess(self, guess: str, target: str) -> float | None:
        if not target:
            return None
        return min(1.0, len(guess) / len(target))


def make_ctx(
    *,
    is_mod: bool = False,
    is_broadcaster: bool = False,
    author_name: str = "viewer",
) -> MagicMock:
    """Return a minimal mock of a TwitchIO Context."""
    ctx = MagicMock()
    ctx.send = AsyncMock()
    ctx.author.is_mod = is_mod
    ctx.author.is_broadcaster = is_broadcaster
    ctx.author.name = author_name
    return ctx


def make_bot(
    prefix: str = "!sx",
    cooldown: int = 5,
    scorer=None,
    on_state_change=None,
) -> StreamantixBot:
    """Return a StreamantixBot instance without connecting to Twitch."""
    bot = object.__new__(StreamantixBot)
    bot._command_prefix = prefix
    bot._cooldown = CooldownManager(cooldown)
    bot._game_state = GameState(scorer=scorer)
    bot._next_difficulty = Difficulty.EASY
    bot._on_state_change = on_state_change
    return bot


@pytest.fixture()
def fake_scorer() -> FakeScorer:
    return FakeScorer()


@pytest.fixture()
def game_state(fake_scorer: FakeScorer) -> GameState:
    return GameState(scorer=fake_scorer)


@pytest.fixture()
def game_state_no_scorer() -> GameState:
    return GameState()
