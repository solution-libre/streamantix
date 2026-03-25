"""Starlette-based WebSocket overlay server.

The server exposes:

* ``GET /`` and ``GET /overlay`` – serve the static HTML overlay page.
* ``WebSocket /ws`` – broadcast game-state JSON to all connected clients.

Usage (standalone)::

    import asyncio
    from overlay.server import OverlayServer

    server = OverlayServer(host="0.0.0.0", port=8080)
    asyncio.run(server.serve())

To integrate with the bot, pass :meth:`OverlayServer.broadcast` as the
``on_state_change`` callback when constructing :class:`~bot.bot.StreamantixBot`.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, Response
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket, WebSocketDisconnect

_STATIC_DIR = pathlib.Path(__file__).parent / "static"


class OverlayServer:
    """HTTP + WebSocket server for the OBS overlay.

    Args:
        host: Interface to bind (default ``"0.0.0.0"``).
        port: TCP port to listen on (default ``8080``).
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self.host = host
        self.port = port
        self._clients: set[WebSocket] = set()
        self._last_state: dict[str, Any] | None = None
        self._app = Starlette(
            routes=[
                Route("/", self._serve_index),
                Route("/overlay", self._serve_index),
                WebSocketRoute("/ws", self._websocket_endpoint),
            ]
        )

    # ------------------------------------------------------------------
    # ASGI app property (useful for testing)
    # ------------------------------------------------------------------

    @property
    def app(self) -> Starlette:
        """The underlying Starlette ASGI application."""
        return self._app

    # ------------------------------------------------------------------
    # HTTP handlers
    # ------------------------------------------------------------------

    async def _serve_index(self, request: Request) -> Response:
        index = _STATIC_DIR / "index.html"
        return FileResponse(str(index))

    # ------------------------------------------------------------------
    # WebSocket handler
    # ------------------------------------------------------------------

    async def _websocket_endpoint(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)
        if self._last_state is not None:
            try:
                await websocket.send_text(json.dumps(self._last_state))
            except Exception:
                self._clients.discard(websocket)
                return
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            self._clients.discard(websocket)

    # ------------------------------------------------------------------
    # Broadcast API
    # ------------------------------------------------------------------

    async def broadcast(self, state: dict[str, Any]) -> None:
        """Send *state* as a JSON text frame to every connected WebSocket client.

        The state is also cached so that clients connecting after the last
        broadcast (e.g. after a page refresh) receive it immediately.

        Dead connections are silently removed.

        Args:
            state: A JSON-serialisable dict (e.g. from
                :func:`~overlay.state.serialize_game_state`).
        """
        self._last_state = state
        if not self._clients:
            return
        message = json.dumps(state)
        dead: set[WebSocket] = set()
        for ws in set(self._clients):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self._clients -= dead

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    async def serve(self) -> None:
        """Run the uvicorn server until stopped.

        This coroutine blocks until the server shuts down, so it should be
        run concurrently with the bot using :func:`asyncio.gather`.
        """
        config = uvicorn.Config(
            self._app,
            host=self.host,
            port=self.port,
            log_level="warning",
        )
        server = uvicorn.Server(config)
        await server.serve()
