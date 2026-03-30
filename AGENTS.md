# Streamantix - Development Guidelines

## Language Guidelines

**Always produce code, comments, documentation, and all written content in English**, even when the conversation is conducted in another language.

This includes:

- Code variable names, function names, class names
- Code comments and documentation
- Git commit messages
- README files and technical documentation
- Log messages and error messages
- Test descriptions

Conversation and responses can be in another language, but all generated content must be in English.

## Code Style

- **Python 3.12+** with type hints for all public functions
- Format according to PEP 8 conventions
- Google-style docstrings for modules, classes, and public functions
- Organized imports: stdlib → third-party (twitchio, gensim, etc.) → local
- Use `from __future__ import annotations` for type hints when needed

## Architecture

The project follows a modular architecture:

```text
bot/         → Twitch bot management (connection, commands, cooldowns)
game/        → Semantic game engine (Word2Vec embeddings, scoring)
overlay/     → Stream overlay web server (Starlette, WebSocket)
auth/        → Twitch OAuth authentication management
```

### Core Principles

- **Centralized configuration**: `config.py` loads environment variables via `.env`
- **Shared game state**: `game.state.GameState` synchronizes data between bot and overlay
- **Async/await**: TwitchIO and Starlette are asynchronous, always use `async/await`
- **Token management**: `auth.twitch_auth.TokenManager` handles automatic refresh

## Development Commands

```bash
# Install dependencies
poetry install

# Run the bot (requires configured .env)
poetry run python main.py

# Run tests with coverage
poetry run pytest

# Run specific tests
poetry run pytest tests/test_engine.py

# Check coverage (target: >80%)
poetry run pytest --cov-report=html
```

## Conventions

### Configuration

- **Always** load environment variables via `config.py`, never use `os.getenv()` directly
- Sensible default values defined in `config.py`
- Secrets (tokens, client ID/secret) must stay out of version control

### Tests

- One test file per module: `tests/test_<module>.py`
- Use `pytest.mark.asyncio` for async functions
- Mock network calls (Twitch API, Word2Vec models in prod)
- Target >80% code coverage

### Error Handling

- Catch specific exceptions, avoid `except Exception` except for logging
- Log errors with context (user, command, timestamp)
- Graceful chat responses on error (no visible stacktrace)

### Word2Vec Models

- The model is large (~700MB), not versioned
- Download via `download_model.py` or Docker volume
- Load once at startup, reuse the instance
