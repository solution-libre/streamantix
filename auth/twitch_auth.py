"""Twitch OAuth Authorization Code flow with automatic token refresh."""

from __future__ import annotations

import json
import secrets
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/authorize"
TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
TWITCH_VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"

# Refresh when less than this many seconds remain before expiry.
_REFRESH_BUFFER_SECONDS = 300


class TokenManager:
    """Manages Twitch OAuth tokens: storage, refresh, and login flow."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:4343/callback",
        scopes: str = "chat:read chat:edit",
        token_path: str = ".secrets/twitch_tokens.json",
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes
        self.token_path = Path(token_path)

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    def load_tokens(self) -> dict[str, Any] | None:
        """Load tokens from the JSON file, or return None if not present."""
        if not self.token_path.exists():
            return None
        with self.token_path.open() as f:
            return json.load(f)  # type: ignore[no-any-return]

    def save_tokens(self, data: dict[str, Any]) -> None:
        """Persist tokens to the JSON file, creating parent dirs as needed."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with self.token_path.open("w") as f:
            json.dump(data, f, indent=2)

    # ------------------------------------------------------------------
    # Validity helpers
    # ------------------------------------------------------------------

    def is_valid(self, tokens: dict[str, Any]) -> bool:
        """Return True if *tokens* contains a non-expired access token."""
        if not tokens.get("access_token"):
            return False
        expires_at = tokens.get("expires_at", 0)
        return time.time() < expires_at - _REFRESH_BUFFER_SECONDS

    def needs_refresh(self, tokens: dict[str, Any]) -> bool:
        """Return True if the token is expired/near-expiry but refreshable."""
        if not tokens.get("access_token") or not tokens.get("refresh_token"):
            return False
        expires_at = tokens.get("expires_at", 0)
        return time.time() >= expires_at - _REFRESH_BUFFER_SECONDS

    # ------------------------------------------------------------------
    # HTTP helpers (stdlib only — no extra runtime dependency)
    # ------------------------------------------------------------------

    def _post(self, url: str, data: dict[str, str]) -> dict[str, Any]:
        encoded = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(url, data=encoded, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req) as resp:  # noqa: S310
            return json.loads(resp.read().decode())  # type: ignore[no-any-return]

    def _validate_with_twitch(self, access_token: str) -> bool:
        """Return True if the token is accepted by the Twitch validate endpoint."""
        req = urllib.request.Request(TWITCH_VALIDATE_URL)
        req.add_header("Authorization", f"OAuth {access_token}")
        try:
            with urllib.request.urlopen(req) as resp:  # noqa: S310
                return resp.status == 200
        except urllib.error.HTTPError:
            return False

    # ------------------------------------------------------------------
    # Token exchange / refresh
    # ------------------------------------------------------------------

    def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange an authorization code for tokens."""
        response = self._post(
            TWITCH_TOKEN_URL,
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            },
        )
        return self._process_token_response(response)

    def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Obtain a new access token using the refresh token."""
        response = self._post(
            TWITCH_TOKEN_URL,
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        return self._process_token_response(response)

    def _process_token_response(self, response: dict[str, Any]) -> dict[str, Any]:
        expires_in = int(response.get("expires_in", 0))
        return {
            "access_token": response["access_token"],
            "refresh_token": response.get("refresh_token", ""),
            "expires_at": int(time.time()) + expires_in,
            "scope": response.get("scope", []),
            "token_type": response.get("token_type", "bearer"),
        }

    # ------------------------------------------------------------------
    # Login flow (local callback server)
    # ------------------------------------------------------------------

    def authorization_url(self, state: str) -> str:
        """Build the Twitch authorization URL including a CSRF state token."""
        params = urllib.parse.urlencode(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "scope": self.scopes,
                "state": state,
            }
        )
        return f"{TWITCH_AUTH_URL}?{params}"

    def _wait_for_code(self, expected_state: str) -> str:
        """Start a local HTTP server and block until the OAuth callback arrives.

        Validates the *state* parameter against *expected_state* to prevent
        CSRF attacks (RFC 6749 §10.12).
        """
        parsed = urllib.parse.urlparse(self.redirect_uri)
        port = parsed.port or 80
        captured: dict[str, str] = {}

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed_path = urllib.parse.urlparse(self.path)
                if parsed_path.path == "/callback":
                    params = urllib.parse.parse_qs(parsed_path.query)
                    received_state = params.get("state", [""])[0]
                    if not secrets.compare_digest(received_state, expected_state):
                        self.send_response(403)
                        self.end_headers()
                        self.wfile.write(b"Invalid state parameter. Possible CSRF attack.")
                        captured["error"] = "csrf"
                        return
                    if "code" in params:
                        captured["code"] = params["code"][0]
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(
                            b"Authorization successful! You can close this tab."
                        )
                    else:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(b"Missing code parameter.")
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A002
                pass  # suppress request logs

        server = HTTPServer(("", port), _Handler)
        server.timeout = 300  # 5-minute window to complete login
        while "code" not in captured and "error" not in captured:
            server.handle_request()
        server.server_close()
        if "error" in captured:
            raise RuntimeError("OAuth login aborted: CSRF state mismatch.")
        return captured["code"]

    def login(self) -> str:
        """Run the full OAuth login flow and return the new access token."""
        state = secrets.token_urlsafe(16)
        url = self.authorization_url(state=state)
        print(f"\nOpen the following URL in your browser to authorize:\n\n  {url}\n")
        print(f"Waiting for OAuth callback on {self.redirect_uri} …")
        code = self._wait_for_code(expected_state=state)
        tokens = self.exchange_code(code)
        self.save_tokens(tokens)
        print("Tokens saved successfully.")
        return tokens["access_token"]

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def get_token(self) -> str:
        """Return a valid access token, refreshing or re-logging-in as needed."""
        tokens = self.load_tokens()
        if tokens and self.is_valid(tokens):
            if self._validate_with_twitch(tokens["access_token"]):
                return tokens["access_token"]
            print("Stored token rejected by Twitch (revoked?). Attempting refresh…")

        if tokens and tokens.get("refresh_token"):
            try:
                tokens = self.refresh_token(tokens["refresh_token"])
                self.save_tokens(tokens)
                return tokens["access_token"]
            except Exception as exc:
                print(f"Token refresh failed ({exc}). Re-authenticating…")

        return self.login()
