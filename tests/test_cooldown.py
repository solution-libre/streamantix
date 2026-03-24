"""Tests for the cooldown system (bot.cooldown)."""

import time

from bot.cooldown import CooldownManager


class TestCooldownManagerInit:
    def test_default_not_on_cooldown(self):
        """A user who has never issued a command should not be on cooldown."""
        mgr = CooldownManager(5)
        assert not mgr.is_on_cooldown("alice")

    def test_cooldown_seconds_stored(self):
        """The cooldown duration should be stored and retrievable."""
        mgr = CooldownManager(10)
        assert mgr.duration == 10


class TestIsOnCooldown:
    def test_user_on_cooldown_after_record(self):
        """A user should be on cooldown immediately after calling record()."""
        mgr = CooldownManager(30)
        mgr.record("alice")
        assert mgr.is_on_cooldown("alice")

    def test_user_not_on_cooldown_after_expiry(self):
        """A user should no longer be on cooldown after the cooldown period expires."""
        mgr = CooldownManager(0)
        mgr.record("alice")
        time.sleep(0.01)
        assert not mgr.is_on_cooldown("alice")

    def test_different_users_tracked_independently(self):
        """Cooldown state should be tracked independently per user."""
        mgr = CooldownManager(30)
        mgr.record("alice")
        assert mgr.is_on_cooldown("alice")
        assert not mgr.is_on_cooldown("bob")


class TestRecord:
    def test_record_updates_timestamp(self):
        """Calling record() should put the user on cooldown immediately."""
        mgr = CooldownManager(30)
        assert not mgr.is_on_cooldown("alice")
        mgr.record("alice")
        assert mgr.is_on_cooldown("alice")

    def test_record_new_user(self):
        """record() should work for a user who has not been seen before."""
        mgr = CooldownManager(30)
        mgr.record("newuser")
        assert mgr.is_on_cooldown("newuser")


class TestCooldownManagerRemaining:
    def test_remaining_zero_when_inactive(self):
        """remaining() should return 0.0 when the user has not been seen."""
        mgr = CooldownManager(5)
        assert mgr.remaining("alice") == 0.0

    def test_remaining_positive_during_cooldown(self):
        """remaining() should return a positive value while user is on cooldown."""
        mgr = CooldownManager(30)
        mgr.record("alice")
        assert mgr.remaining("alice") > 0

    def test_remaining_never_negative(self):
        """remaining() should never return a negative value after expiry."""
        mgr = CooldownManager(0)
        mgr.record("alice")
        time.sleep(0.01)
        assert mgr.remaining("alice") == 0.0

    def test_remaining_independent_per_user(self):
        """remaining() for one user should not affect another user."""
        mgr = CooldownManager(30)
        mgr.record("alice")
        assert mgr.remaining("alice") > 0
        assert mgr.remaining("bob") == 0.0


class TestCooldownManagerSetDuration:
    def test_set_duration_updates_value(self):
        """set_duration() should update the cooldown duration."""
        mgr = CooldownManager(5)
        mgr.set_duration(15)
        assert mgr.duration == 15

    def test_set_duration_zero_disables_cooldown(self):
        """Setting duration to 0 should disable the cooldown for a user."""
        mgr = CooldownManager(30)
        mgr.record("alice")
        mgr.set_duration(0)
        assert not mgr.is_on_cooldown("alice")

