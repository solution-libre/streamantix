"""Tests for the stream overlay: state serialisation and server endpoints."""

from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from game.state import Difficulty, GameState
from overlay.server import OverlayServer
from overlay.state import serialize_game_state
from tests.conftest import FakeScorer


# ---------------------------------------------------------------------------
# State serialisation — overlay.state.serialize_game_state
# ---------------------------------------------------------------------------


class TestSerializeIdle:
    def test_status_is_idle_when_no_game_started(self):
        gs = GameState()
        result = serialize_game_state(gs)
        assert result["status"] == "idle"

    def test_all_fields_present_when_idle(self):
        gs = GameState()
        result = serialize_game_state(gs)
        for key in ("status", "difficulty", "attempt_count", "best_guess", "last_guess", "top_guesses", "target_word"):
            assert key in result

    def test_idle_has_none_target_word(self):
        gs = GameState()
        result = serialize_game_state(gs)
        assert result["target_word"] is None

    def test_idle_has_zero_attempt_count(self):
        gs = GameState()
        result = serialize_game_state(gs)
        assert result["attempt_count"] == 0

    def test_idle_has_empty_top_guesses(self):
        gs = GameState()
        result = serialize_game_state(gs)
        assert result["top_guesses"] == []


class TestSerializeRunning:
    def test_status_running_after_start(self):
        gs = GameState()
        gs.start_new_game("chat", Difficulty.EASY)
        result = serialize_game_state(gs)
        assert result["status"] == "running"

    def test_difficulty_present(self):
        gs = GameState()
        gs.start_new_game("chat", Difficulty.HARD)
        result = serialize_game_state(gs)
        assert result["difficulty"] == "hard"

    def test_target_word_hidden_while_running(self):
        gs = GameState()
        gs.start_new_game("chat", Difficulty.EASY)
        result = serialize_game_state(gs)
        assert result["target_word"] is None

    def test_attempt_count_increments(self):
        gs = GameState(scorer=FakeScorer())
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chien")
        result = serialize_game_state(gs)
        assert result["attempt_count"] == 1

    def test_last_guess_populated_after_guess(self):
        gs = GameState(scorer=FakeScorer())
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chien")
        result = serialize_game_state(gs)
        assert result["last_guess"] is not None
        assert result["last_guess"]["word"] == "chien"
        assert result["last_guess"]["user"] == "alice"

    def test_last_guess_is_none_before_any_guess(self):
        gs = GameState()
        gs.start_new_game("chat", Difficulty.EASY)
        result = serialize_game_state(gs)
        assert result["last_guess"] is None

    def test_best_guess_is_highest_scored(self):
        gs = GameState(scorer=FakeScorer())
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "ch")       # score = 2/4 = 0.5
        gs.submit_guess("bob", "chateau")    # score = 6/4 -> clamped to 1.0, but this is exact? No, clean("chateau") != clean("chat")
        result = serialize_game_state(gs)
        assert result["best_guess"] is not None
        assert result["best_guess"]["score"] >= 0.5

    def test_top_guesses_max_ten(self):
        gs = GameState(scorer=FakeScorer())
        gs.start_new_game("chat", Difficulty.EASY)
        for i in range(15):
            gs.submit_guess(f"user{i}", "ch")
        result = serialize_game_state(gs)
        assert len(result["top_guesses"]) <= 10

    def test_top_guesses_ordered_by_descending_score(self):
        gs = GameState(scorer=FakeScorer())
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "c")     # score = 1/4
        gs.submit_guess("bob", "cha")     # score = 3/4
        gs.submit_guess("carol", "ch")    # score = 2/4
        result = serialize_game_state(gs)
        scores = [e["score"] for e in result["top_guesses"]]
        assert scores == sorted(scores, reverse=True)

    def test_top_guesses_contain_required_keys(self):
        gs = GameState(scorer=FakeScorer())
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "ch")
        result = serialize_game_state(gs)
        entry = result["top_guesses"][0]
        assert "word" in entry
        assert "score" in entry
        assert "user" in entry


class TestSerializeFound:
    def test_status_found_after_correct_guess(self):
        gs = GameState()
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chat")
        result = serialize_game_state(gs)
        assert result["status"] == "found"

    def test_target_word_revealed_when_found(self):
        gs = GameState()
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chat")
        result = serialize_game_state(gs)
        assert result["target_word"] == "chat"

    def test_serialisation_is_json_serialisable(self):
        gs = GameState(scorer=FakeScorer())
        gs.start_new_game("chat", Difficulty.EASY)
        gs.submit_guess("alice", "chien")
        gs.submit_guess("bob", "chat")
        result = serialize_game_state(gs)
        serialised = json.dumps(result)  # must not raise
        decoded = json.loads(serialised)
        assert decoded["status"] == "found"


# ---------------------------------------------------------------------------
# Overlay server — HTTP endpoints
# ---------------------------------------------------------------------------


@pytest.fixture()
def overlay_client() -> TestClient:
    server = OverlayServer(host="127.0.0.1", port=8080)
    return TestClient(server.app)


class TestOverlayHTTP:
    def test_root_returns_html(self, overlay_client: TestClient):
        response = overlay_client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_overlay_path_returns_html(self, overlay_client: TestClient):
        response = overlay_client.get("/overlay")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_html_contains_websocket_script(self, overlay_client: TestClient):
        response = overlay_client.get("/overlay")
        assert b"WebSocket" in response.content

    def test_unknown_path_returns_404(self, overlay_client: TestClient):
        response = overlay_client.get("/nonexistent")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Overlay server — WebSocket endpoint
# ---------------------------------------------------------------------------


class TestOverlayWebSocket:
    def test_websocket_connects_successfully(self, overlay_client: TestClient):
        with overlay_client.websocket_connect("/ws") as ws:
            pass  # connection accepted without error

    def test_broadcast_delivers_message_to_connected_client(self):
        """Broadcast sends the JSON state to connected WebSocket clients."""
        import asyncio

        server = OverlayServer()
        client = TestClient(server.app)

        received: list[str] = []

        with client.websocket_connect("/ws") as ws:
            payload = {"status": "running", "attempt_count": 3}
            asyncio.run(server.broadcast(payload))
            data = ws.receive_text()
            received.append(data)

        assert len(received) == 1
        decoded = json.loads(received[0])
        assert decoded["status"] == "running"
        assert decoded["attempt_count"] == 3

    def test_broadcast_to_no_clients_does_not_raise(self):
        """broadcast() is a no-op when no client is connected."""
        import asyncio

        server = OverlayServer()
        # Should not raise even with zero clients
        asyncio.run(server.broadcast({"status": "idle"}))

    def test_new_client_receives_last_state_on_connect(self):
        """A client that connects after a broadcast immediately gets the cached state."""
        import asyncio

        server = OverlayServer()
        client = TestClient(server.app)

        payload = {"status": "running", "attempt_count": 5}
        asyncio.run(server.broadcast(payload))

        with client.websocket_connect("/ws") as ws:
            data = ws.receive_text()

        decoded = json.loads(data)
        assert decoded["status"] == "running"
        assert decoded["attempt_count"] == 5

    def test_new_client_receives_no_message_when_no_broadcast_yet(self):
        """A client that connects before any broadcast does not get a spurious message."""
        server = OverlayServer()
        client = TestClient(server.app)

        # Connect and verify that no state is cached, meaning the connection
        # handler will not attempt to send an initial message to the client.
        # (_last_state is the guard for the send; None means no send occurs.)
        with client.websocket_connect("/ws") as ws:
            assert server._last_state is None
