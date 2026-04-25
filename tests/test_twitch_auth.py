"""Tests for auth.twitch_auth.TokenManager."""

from __future__ import annotations

import json
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from auth.twitch_auth import TokenManager, _REFRESH_BUFFER_SECONDS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager(tmp_path) -> TokenManager:
    return TokenManager(
        client_id="cid",
        client_secret="csecret",
        token_path=str(tmp_path / ".secrets" / "twitch_tokens.json"),
    )


def _make_manager_on_port(tmp_path, port: int) -> TokenManager:
    return TokenManager(
        client_id="cid",
        client_secret="csecret",
        redirect_uri=f"http://localhost:{port}/callback",
        token_path=str(tmp_path / ".secrets" / "twitch_tokens.json"),
    )


def _free_port() -> int:
    """Return an available TCP port on localhost."""
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _wait_for_server(port: int, timeout: float = 3.0) -> None:
    """Block until the TCP port is accepting connections or timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("localhost", port), timeout=0.05):
                return
        except OSError:
            time.sleep(0.02)
    raise TimeoutError(f"Server on port {port} did not start in time.")


def _make_token_data(expires_delta: int = 3600) -> dict[str, Any]:
    return {
        "access_token": "tok_abc",
        "refresh_token": "ref_xyz",
        "expires_at": int(time.time()) + expires_delta,
        "scope": ["chat:read", "chat:edit"],
        "token_type": "bearer",
    }


# ---------------------------------------------------------------------------
# TestTokenStorage
# ---------------------------------------------------------------------------


class TestTokenStorage:
    def test_load_returns_none_when_file_missing(self, tmp_path):
        manager = _make_manager(tmp_path)
        assert manager.load_tokens() is None

    def test_save_and_load_roundtrip(self, tmp_path):
        manager = _make_manager(tmp_path)
        data = _make_token_data()
        manager.save_tokens(data)
        loaded = manager.load_tokens()
        assert loaded == data

    def test_save_creates_parent_directory(self, tmp_path):
        manager = _make_manager(tmp_path)
        manager.save_tokens(_make_token_data())
        assert manager.token_path.exists()

    def test_save_writes_valid_json(self, tmp_path):
        manager = _make_manager(tmp_path)
        data = _make_token_data()
        manager.save_tokens(data)
        raw = manager.token_path.read_text()
        parsed = json.loads(raw)
        assert parsed["access_token"] == "tok_abc"


# ---------------------------------------------------------------------------
# TestTokenValidity
# ---------------------------------------------------------------------------


class TestTokenValidity:
    def test_valid_token_returns_true(self, tmp_path):
        manager = _make_manager(tmp_path)
        tokens = _make_token_data(expires_delta=3600)
        assert manager.is_valid(tokens) is True

    def test_expired_token_returns_false(self, tmp_path):
        manager = _make_manager(tmp_path)
        tokens = _make_token_data(expires_delta=-10)
        assert manager.is_valid(tokens) is False

    def test_near_expiry_token_invalid(self, tmp_path):
        manager = _make_manager(tmp_path)
        tokens = _make_token_data(expires_delta=_REFRESH_BUFFER_SECONDS - 1)
        assert manager.is_valid(tokens) is False

    def test_missing_access_token_is_invalid(self, tmp_path):
        manager = _make_manager(tmp_path)
        assert manager.is_valid({}) is False

    def test_needs_refresh_when_near_expiry(self, tmp_path):
        manager = _make_manager(tmp_path)
        tokens = _make_token_data(expires_delta=_REFRESH_BUFFER_SECONDS - 1)
        assert manager.needs_refresh(tokens) is True

    def test_no_refresh_needed_for_valid_token(self, tmp_path):
        manager = _make_manager(tmp_path)
        tokens = _make_token_data(expires_delta=3600)
        assert manager.needs_refresh(tokens) is False

    def test_no_refresh_without_refresh_token(self, tmp_path):
        manager = _make_manager(tmp_path)
        tokens = _make_token_data(expires_delta=-10)
        tokens["refresh_token"] = ""
        assert manager.needs_refresh(tokens) is False


# ---------------------------------------------------------------------------
# TestAuthorizationUrl
# ---------------------------------------------------------------------------


class TestAuthorizationUrl:
    def test_contains_client_id(self, tmp_path):
        manager = _make_manager(tmp_path)
        url = manager.authorization_url(state="teststate")
        assert "client_id=cid" in url

    def test_contains_response_type_code(self, tmp_path):
        manager = _make_manager(tmp_path)
        url = manager.authorization_url(state="teststate")
        assert "response_type=code" in url

    def test_contains_scopes(self, tmp_path):
        manager = _make_manager(tmp_path)
        url = manager.authorization_url(state="teststate")
        assert "scope=" in url

    def test_contains_state_parameter(self, tmp_path):
        manager = _make_manager(tmp_path)
        url = manager.authorization_url(state="mycsrftoken")
        assert "state=mycsrftoken" in url


# ---------------------------------------------------------------------------
# TestTokenExchangeAndRefresh  (mocked HTTP)
# ---------------------------------------------------------------------------


class TestTokenExchangeAndRefresh:
    def _fake_response(self) -> dict[str, Any]:
        return {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_in": 14400,
            "scope": ["chat:read", "chat:edit"],
            "token_type": "bearer",
        }

    def test_exchange_code_returns_processed_tokens(self, tmp_path):
        manager = _make_manager(tmp_path)
        with patch.object(manager, "_post", return_value=self._fake_response()) as mock_post:
            tokens = manager.exchange_code("auth_code_123")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[0][1]  # second positional arg is the data dict
        assert call_kwargs["grant_type"] == "authorization_code"
        assert call_kwargs["code"] == "auth_code_123"
        assert tokens["access_token"] == "new_access"
        assert tokens["refresh_token"] == "new_refresh"
        assert tokens["expires_at"] > int(time.time())

    def test_refresh_token_returns_processed_tokens(self, tmp_path):
        manager = _make_manager(tmp_path)
        with patch.object(manager, "_post", return_value=self._fake_response()) as mock_post:
            tokens = manager.refresh_token("old_refresh_token")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[0][1]
        assert call_kwargs["grant_type"] == "refresh_token"
        assert call_kwargs["refresh_token"] == "old_refresh_token"
        assert tokens["access_token"] == "new_access"

    def test_refresh_token_uses_client_credentials(self, tmp_path):
        manager = _make_manager(tmp_path)
        with patch.object(manager, "_post", return_value=self._fake_response()) as mock_post:
            manager.refresh_token("some_refresh")
        data = mock_post.call_args[0][1]
        assert data["client_id"] == "cid"
        assert data["client_secret"] == "csecret"


# ---------------------------------------------------------------------------
# TestGetToken  (integration of storage + validity + refresh + login)
# ---------------------------------------------------------------------------


class TestGetToken:
    def test_returns_stored_valid_token(self, tmp_path):
        manager = _make_manager(tmp_path)
        data = _make_token_data(expires_delta=3600)
        manager.save_tokens(data)
        with patch.object(manager, "_validate_with_twitch", return_value=True):
            assert manager.get_token() == "tok_abc"

    def test_relogins_when_token_revoked_by_twitch(self, tmp_path):
        manager = _make_manager(tmp_path)
        data = _make_token_data(expires_delta=3600)
        manager.save_tokens(data)

        refreshed = {
            "access_token": "refreshed_tok",
            "refresh_token": "new_ref",
            "expires_in": 14400,
            "scope": [],
            "token_type": "bearer",
        }
        with (
            patch.object(manager, "_validate_with_twitch", return_value=False),
            patch.object(manager, "_post", return_value=refreshed),
        ):
            token = manager.get_token()

        assert token == "refreshed_tok"

    def test_refreshes_near_expiry_token(self, tmp_path):
        manager = _make_manager(tmp_path)
        data = _make_token_data(expires_delta=_REFRESH_BUFFER_SECONDS - 1)
        manager.save_tokens(data)

        refreshed = {
            "access_token": "refreshed_tok",
            "refresh_token": "new_ref",
            "expires_in": 14400,
            "scope": [],
            "token_type": "bearer",
        }
        with patch.object(manager, "_post", return_value=refreshed):
            token = manager.get_token()

        assert token == "refreshed_tok"

    def test_falls_back_to_login_when_refresh_fails(self, tmp_path):
        manager = _make_manager(tmp_path)
        data = _make_token_data(expires_delta=_REFRESH_BUFFER_SECONDS - 1)
        manager.save_tokens(data)

        with (
            patch.object(manager, "_post", side_effect=Exception("network error")),
            patch.object(manager, "login", return_value="login_tok") as mock_login,
        ):
            token = manager.get_token()

        mock_login.assert_called_once()
        assert token == "login_tok"

    def test_triggers_login_when_no_stored_token(self, tmp_path):
        manager = _make_manager(tmp_path)
        with patch.object(manager, "login", return_value="brand_new_tok") as mock_login:
            token = manager.get_token()

        mock_login.assert_called_once()
        assert token == "brand_new_tok"


# ---------------------------------------------------------------------------
# TestCsrfStateValidation
# ---------------------------------------------------------------------------


class TestCsrfStateValidation:
    """Verify that _wait_for_code rejects callbacks with a mismatched state."""

    def _call_callback(self, port: int, **params: str) -> int:
        """Fire a GET /callback request and return the HTTP status code."""
        query = urllib.parse.urlencode(params)
        url = f"http://localhost:{port}/callback?{query}"
        try:
            with urllib.request.urlopen(url) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            return exc.code
        except urllib.error.URLError:
            return 0  # server already closed

    def test_login_generates_unique_states(self, tmp_path):
        """Each login call must use a distinct state value."""
        manager = _make_manager(tmp_path)
        states: list[str] = []

        def capture_url(state: str) -> str:
            states.append(state)
            return f"https://example.com?state={state}"

        _fake_tokens = {
            "access_token": "tok",
            "refresh_token": "",
            "expires_at": 9999,
            "scope": [],
            "token_type": "bearer",
        }
        with (
            patch.object(manager, "authorization_url", side_effect=capture_url),
            patch.object(manager, "_wait_for_code", return_value="code_x"),
            patch.object(manager, "exchange_code", return_value=_fake_tokens),
            patch.object(manager, "save_tokens"),
            patch("builtins.print"),
        ):
            manager.login()
            manager.login()

        assert len(states) == 2
        assert states[0] != states[1]

    def test_wait_for_code_passes_expected_state_to_login(self, tmp_path):
        """login() must forward the generated state to _wait_for_code."""
        manager = _make_manager(tmp_path)
        received: dict[str, str] = {}

        def capture_wait(expected_state: str) -> str:
            received["state"] = expected_state
            return "auth_code"

        captured_url: list[str] = []

        def capture_url(state: str) -> str:
            captured_url.append(state)
            return f"https://example.com?state={state}"

        _fake_tokens = {
            "access_token": "tok",
            "refresh_token": "",
            "expires_at": 9999,
            "scope": [],
            "token_type": "bearer",
        }
        with (
            patch.object(manager, "authorization_url", side_effect=capture_url),
            patch.object(manager, "_wait_for_code", side_effect=capture_wait),
            patch.object(manager, "exchange_code", return_value=_fake_tokens),
            patch.object(manager, "save_tokens"),
            patch("builtins.print"),
        ):
            manager.login()

        # The state passed to authorization_url and _wait_for_code must match
        assert captured_url[0] == received["state"]

    def test_wrong_state_returns_403_and_aborts(self, tmp_path):
        """_wait_for_code must reject a mismatched state with HTTP 403 and raise."""
        port = _free_port()
        manager = _make_manager_on_port(tmp_path, port)
        result: dict[str, object] = {}

        def run_server() -> None:
            try:
                result["code"] = manager._wait_for_code("correct-state")
            except RuntimeError as exc:
                result["error"] = str(exc)

        t = threading.Thread(target=run_server, daemon=True)
        t.start()
        _wait_for_server(port)

        status = self._call_callback(port, code="stolen", state="wrong-state")
        assert status == 403

        # Server aborts after CSRF mismatch — no unblock needed
        t.join(timeout=5)
        assert "code" not in result
        assert "CSRF" in str(result.get("error", ""))

    def test_correct_state_captures_code(self, tmp_path):
        """_wait_for_code must accept a matching state and return the code."""
        port = _free_port()
        manager = _make_manager_on_port(tmp_path, port)
        result: dict[str, object] = {}

        def run_server() -> None:
            result["code"] = manager._wait_for_code("valid-state")

        t = threading.Thread(target=run_server, daemon=True)
        t.start()
        _wait_for_server(port)

        self._call_callback(port, code="auth_code_ok", state="valid-state")
        t.join(timeout=5)
        assert result.get("code") == "auth_code_ok"

    def test_missing_state_param_returns_403(self, tmp_path):
        """A callback with no state parameter must be rejected as a CSRF attempt."""
        port = _free_port()
        manager = _make_manager_on_port(tmp_path, port)
        result: dict[str, object] = {}

        def run_server() -> None:
            try:
                result["code"] = manager._wait_for_code("expected")
            except RuntimeError as exc:
                result["error"] = str(exc)

        t = threading.Thread(target=run_server, daemon=True)
        t.start()
        _wait_for_server(port)

        # Request without state — compare_digest("", "expected") → False → 403
        status = self._call_callback(port, code="evil_code")
        assert status == 403

        t.join(timeout=5)
        assert "CSRF" in str(result.get("error", ""))
