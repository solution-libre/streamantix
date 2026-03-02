"""Skeleton tests for command parsing and permission checks (bot.bot)."""

import pytest


class TestCommandParsing:
    @pytest.mark.skip(reason="not implemented")
    def test_guess_command_parses_word(self):
        """The !guess command should extract the submitted word from the message."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="not implemented")
    def test_guess_command_ignores_extra_args(self):
        """The !guess command should handle extra arguments gracefully."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="not implemented")
    def test_unknown_command_is_ignored(self):
        """Unknown commands should not raise an error."""
        assert False, "not implemented"


class TestPermissionChecks:
    @pytest.mark.skip(reason="not implemented")
    def test_moderator_can_start_game(self):
        """Only moderators (or the broadcaster) should be able to start a game."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="not implemented")
    def test_regular_user_cannot_start_game(self):
        """Regular users should not be permitted to start a game."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="not implemented")
    def test_any_user_can_guess(self):
        """Any user in the channel should be able to submit a guess."""
        assert False, "not implemented"


class TestCooldownEnforcement:
    @pytest.mark.skip(reason="not implemented")
    def test_command_rejected_when_user_on_cooldown(self):
        """A command from a user on cooldown should be rejected."""
        assert False, "not implemented"

    @pytest.mark.skip(reason="not implemented")
    def test_command_accepted_after_cooldown_expires(self):
        """A command should be accepted once the user's cooldown has expired."""
        assert False, "not implemented"
