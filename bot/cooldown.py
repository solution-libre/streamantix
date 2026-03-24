"""Cooldown tracking for bot commands."""

import time


class CooldownManager:
    """Track the last command time for each user to enforce cooldowns."""

    def __init__(self, cooldown_seconds: int) -> None:
        self._cooldown = cooldown_seconds
        self._last_used: dict[str, float] = {}

    @property
    def duration(self) -> int:
        """Return the current cooldown duration in seconds."""
        return self._cooldown

    def is_on_cooldown(self, user: str) -> bool:
        """Return True if *user* is still on cooldown."""
        last = self._last_used.get(user, 0.0)
        return (time.monotonic() - last) < self._cooldown

    def remaining(self, user: str) -> float:
        """Return seconds remaining in the cooldown for *user* (0.0 if not active)."""
        last = self._last_used.get(user, 0.0)
        elapsed = time.monotonic() - last
        return max(0.0, self._cooldown - elapsed)

    def record(self, user: str) -> None:
        """Record that *user* just used a command."""
        self._last_used[user] = time.monotonic()

    def set_duration(self, seconds: int) -> None:
        """Update the cooldown duration."""
        self._cooldown = seconds

