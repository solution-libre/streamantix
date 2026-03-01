"""Skeleton tests for the cooldown system (bot.cooldown.CooldownManager)."""

import pytest

from bot.cooldown import CooldownManager


class TestCooldownManagerInit:
    @pytest.mark.skip(reason="not implemented")
    def test_default_not_on_cooldown(self):
        """A user who has never issued a command should not be on cooldown."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="not implemented")
    def test_cooldown_seconds_stored(self):
        """The cooldown duration should be stored and retrievable."""
        assert False, "not implemented"


class TestIsOnCooldown:
    @pytest.mark.skip(reason="not implemented")
    def test_user_on_cooldown_after_record(self):
        """A user should be on cooldown immediately after calling record()."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="not implemented")
    def test_user_not_on_cooldown_after_expiry(self):
        """A user should no longer be on cooldown after the cooldown period expires."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="not implemented")
    def test_different_users_tracked_independently(self):
        """Cooldown state should be tracked independently per user."""
        assert False, "not implemented"


class TestRecord:
    @pytest.mark.skip(reason="not implemented")
    def test_record_updates_timestamp(self):
        """Calling record() should update the stored timestamp for the user."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="not implemented")
    def test_record_new_user(self):
        """record() should work for a user who has not been seen before."""
        assert False, "not implemented"
