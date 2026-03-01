"""Per-user cooldown tracking for bot commands."""

import time


class CooldownManager:
    """Track the last command time for each user to enforce cooldowns."""

    def __init__(self, cooldown_seconds: int) -> None:
        self._cooldown = cooldown_seconds
        self._last_used: dict[str, float] = {}

    def is_on_cooldown(self, user: str) -> bool:
        """Return True if *user* is still on cooldown."""
        last = self._last_used.get(user, 0.0)
        return (time.monotonic() - last) < self._cooldown

    def record(self, user: str) -> None:
        """Record that *user* just used a command."""
        self._last_used[user] = time.monotonic()
