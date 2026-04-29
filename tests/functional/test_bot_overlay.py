"""Functional tests: bot ↔ overlay WebSocket integration."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import patch

from starlette.testclient import TestClient

from bot.bot import StreamantixBot
from game.state import Difficulty
from overlay.server import OverlayServer
from tests.conftest import FakeScorer, make_bot, make_ctx

_start_fn = StreamantixBot.start_game._callback
_guess_fn = StreamantixBot.guess._callback
_solution_fn = StreamantixBot.solution._callback


# ---------------------------------------------------------------------------
# TestBotOverlayIntegration — verify what a WS client receives after bot commands
# ---------------------------------------------------------------------------


class TestBotOverlayIntegration:
    def test_start_game_broadcasts_running_state(self):
        overlay = OverlayServer()
        bot = make_bot(cooldown=0, on_state_change=overlay.broadcast)
        client = TestClient(overlay.app)

        ctx = make_ctx(is_broadcaster=True)
        with client.websocket_connect("/ws") as ws:
            with patch("bot.bot.load_word_list", return_value=["chat"]):
                asyncio.run(_start_fn(bot, ctx))
            data = json.loads(ws.receive_text())

        assert data["status"] == "running"
        assert data["difficulty"] == "easy"

    def test_guess_broadcasts_updated_attempt_count(self):
        overlay = OverlayServer()
        bot = make_bot(cooldown=0, scorer=FakeScorer(), on_state_change=overlay.broadcast)
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        client = TestClient(overlay.app)

        ctx = make_ctx(author_name="alice")
        with client.websocket_connect("/ws") as ws:
            asyncio.run(_guess_fn(bot, ctx, "chien"))
            data = json.loads(ws.receive_text())

        assert data["attempt_count"] == 1
        assert data["last_guess"]["word"] == "chien"
        assert data["last_guess"]["user"] == "alice"

    def test_win_broadcasts_found_state(self):
        overlay = OverlayServer()
        bot = make_bot(cooldown=0, on_state_change=overlay.broadcast)
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        client = TestClient(overlay.app)

        ctx = make_ctx(author_name="alice")
        with client.websocket_connect("/ws") as ws:
            asyncio.run(_guess_fn(bot, ctx, "chat"))
            data = json.loads(ws.receive_text())

        assert data["status"] == "found"
        assert data["target_word"] == "chat"

    def test_solution_broadcasts_found_state(self):
        overlay = OverlayServer()
        bot = make_bot(cooldown=0, on_state_change=overlay.broadcast)
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        client = TestClient(overlay.app)

        ctx = make_ctx(is_broadcaster=True, author_name="broadcaster")
        with client.websocket_connect("/ws") as ws:
            asyncio.run(_solution_fn(bot, ctx))
            data = json.loads(ws.receive_text())

        assert data["status"] == "found"


# ---------------------------------------------------------------------------
# TestOverlayWebSocketMultiClient — multiple simultaneous WS connections
# ---------------------------------------------------------------------------


class TestOverlayWebSocketMultiClient:
    def test_broadcast_reaches_all_connected_clients(self):
        """All connected WebSocket clients receive the same broadcast payload."""
        overlay = OverlayServer()
        bot = make_bot(cooldown=0, on_state_change=overlay.broadcast)
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        client = TestClient(overlay.app)

        ctx = make_ctx(author_name="alice")
        with client.websocket_connect("/ws") as ws1:
            with client.websocket_connect("/ws") as ws2:
                asyncio.run(_guess_fn(bot, ctx, "chat"))
                data1 = json.loads(ws1.receive_text())
                data2 = json.loads(ws2.receive_text())

        assert data1["status"] == "found"
        assert data2["status"] == "found"
        assert data1["target_word"] == data2["target_word"] == "chat"

    def test_late_client_receives_cached_state(self):
        overlay = OverlayServer()
        bot = make_bot(cooldown=0, on_state_change=overlay.broadcast)
        # Trigger a broadcast before any WS client connects
        bot._game_state.start_new_game("chat", Difficulty.EASY)
        asyncio.run(bot._notify_overlay())
        assert overlay._last_state is not None

        client = TestClient(overlay.app)
        with client.websocket_connect("/ws") as ws:
            data = json.loads(ws.receive_text())

        assert data["status"] == "running"
