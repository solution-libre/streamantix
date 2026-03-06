# Streamantix

Twitch chat bot to play a Cemantix-like semantic word guessing game.

Players guess a secret word by submitting words in chat. The bot uses word embeddings
(via Gensim) to score each guess based on its semantic similarity to the target word.

## Requirements

- Python 3.12+
- [Poetry](https://python-poetry.org/) for dependency management
- A Twitch account (with either a manually generated OAuth token **or** a
  registered Twitch Developer application for the full OAuth flow)

## Setup

1. **Install dependencies**

   ```bash
   poetry install
   ```

2. **Configure environment variables**

   Copy the example environment file and fill in your values:

   ```bash
   cp .env.example .env
   ```

   | Variable               | Description                                                    | Default |
   |------------------------|----------------------------------------------------------------|---------|
   | `TWITCH_TOKEN`         | Manual OAuth token (`oauth:…`) — optional if using OAuth flow | —       |
   | `TWITCH_CHANNEL`       | Twitch channel name to join — **required**                     | —       |
   | `TWITCH_CLIENT_ID`     | Twitch app client ID (OAuth flow)                              | —       |
   | `TWITCH_CLIENT_SECRET` | Twitch app client secret (OAuth flow)                          | —       |
   | `TWITCH_REDIRECT_URI`  | OAuth redirect URI                                             | `http://localhost:4343/callback` |
   | `TWITCH_SCOPES`        | Space-separated OAuth scopes                                   | `chat:read chat:edit` |
   | `TWITCH_TOKEN_PATH`    | Path to the JSON token storage file                            | `.secrets/twitch_tokens.json` |
   | `COMMAND_PREFIX`       | Prefix for bot commands                                        | `!sx`   |
   | `COOLDOWN`             | Cooldown between guesses (seconds)                             | `5`     |
   | `DIFFICULTY`           | Game difficulty (`easy`=facile, `hard`=difficile)              | `easy`  |
   | `MODEL_PATH`           | Path to the Word2Vec binary model file                         | `models/frWac_no_postag_no_phrase_700_skip_cut50.bin` |
   | `OVERLAY_ENABLED`      | Start the web overlay server                                   | `false` |
   | `OVERLAY_PORT`         | TCP port for the overlay server                                | `8080`  |

## Twitch Authentication

There are two ways to authenticate the bot with Twitch.

### Option A — Manual token (quick start)

Set `TWITCH_TOKEN` to an OAuth token you generate manually:

```env
TWITCH_TOKEN=oauth:xxxxxxxxxx
```

The bot will use this token directly, skipping the OAuth flow entirely.

### Option B — OAuth Authorization Code flow (recommended)

This approach lets the bot obtain and automatically refresh tokens without
you ever copying a token manually.

#### 1. Create a Twitch Developer application

1. Go to <https://dev.twitch.tv/console/apps> and click **Register Your Application**.
2. Fill in a name (e.g. `streamantix-bot`) and set the **OAuth Redirect URL** to
   `http://localhost:4343/callback` (or whatever you set `TWITCH_REDIRECT_URI` to).
3. Choose **Chat Bot** as the category, then click **Create**.
4. Copy the **Client ID** and generate a **Client Secret**.

#### 2. Configure your `.env`

```env
# Leave TWITCH_TOKEN unset (or remove it entirely)
TWITCH_CLIENT_ID=<your_client_id>
TWITCH_CLIENT_SECRET=<your_client_secret>
TWITCH_REDIRECT_URI=http://localhost:4343/callback
TWITCH_SCOPES=chat:read chat:edit
TWITCH_TOKEN_PATH=.secrets/twitch_tokens.json
TWITCH_CHANNEL=your_channel_name
```

#### 3. First-time login

Run the dedicated login command once:

```bash
poetry run python main.py auth-login
```

This will:
1. Print an authorization URL — open it in your browser.
2. Start a temporary local HTTP server on port 4343.
3. After you click **Authorize** on the Twitch page, capture the code and
   exchange it for an `access_token` + `refresh_token`.
4. Save the tokens to `.secrets/twitch_tokens.json` (automatically gitignored).

#### 4. Normal startup

```bash
poetry run python main.py
```

On each start the bot:

- Loads the stored token.
- Uses it if still valid (more than 5 minutes remaining).
- Refreshes it automatically if it is near expiry or expired.
- Falls back to the full login flow only if the refresh token is also invalid.

The `.secrets/` directory is gitignored to prevent accidentally committing tokens.

3. **Download the word embedding model**

   ```bash
   poetry run python download_model.py
   ```

   This downloads the required French Word2Vec model into the `models/`
   directory (which is not versioned).

   ### Model details

   | Property       | Value |
   |----------------|-------|
   | Filename       | `frWac_no_postag_no_phrase_700_skip_cut50.bin` |
   | Source         | <https://embeddings.net/embeddings/frWac_no_postag_no_phrase_700_skip_cut50.bin> |
   | Format         | Binary Word2Vec (gensim `KeyedVectors`) |
   | Approx. size   | ~1 GB |
   | Licence        | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) — please attribute *ATILF / CNRS & Université de Lorraine* |

   To use a different model, set the `MODEL_PATH` environment variable before
   starting the bot:

   ```bash
   MODEL_PATH=/path/to/your/model.bin poetry run python main.py
   ```

## Word Lists

The `data/` directory contains the curated French words that the bot can pick as the
secret target word for each game round.

| File                     | Difficulty | Description |
|--------------------------|------------|-------------|
| `interest_words_f.txt`   | Facile (easy)      | Common, concrete everyday nouns |
| `interest_words_d.txt`   | Difficile (hard)   | Abstract or less frequent words |

Each file uses one word per line. Lines starting with `#` are treated as comments and
are ignored by the word loader. You can add, remove, or replace words freely — just keep
one word per line and ensure every word is present in your word2vec model vocabulary.

## Commands

All commands are prefixed with the configured `COMMAND_PREFIX` (default: `!sx`).

| Command | Who can use | Description |
|---------|-------------|-------------|
| `!sx help` | Anyone | Show available commands |
| `!sx start [easy\|medium\|hard]` | Broadcaster only | Start a new game round. Defaults to the difficulty set with `setdifficulty` (initially `easy`) |
| `!sx guess <word>` | Anyone | Submit a guess for the current game |
| `!sx hint` | Anyone | Show the top 10 best guesses so far (proximity leaderboard) |
| `!sx status` | Anyone | Show current game status: attempts, best guess, and whether the word has been found |
| `!sx setprefix <prefix>` | Mod / Broadcaster | Change the command prefix (session only) |
| `!sx setcooldown <seconds>` | Mod / Broadcaster | Change the guess cooldown duration (session only) |
| `!sx setdifficulty <easy\|hard>` | Mod / Broadcaster | Set the difficulty for the **next** game (session only; does not affect the current game) |

### Examples

```text
!sx help
!sx start
!sx start hard
!sx guess maison
!sx hint
!sx status
!sx setprefix ?sx
!sx setcooldown 10
!sx setdifficulty hard
```

## Testing

Run the full test suite:

```bash
poetry run pytest
```

Run with coverage report:

```bash
poetry run pytest --cov
```

## Changing the Command Prefix

By default the bot listens for commands starting with `!sx` (e.g. `!sx guess chat`).
You can configure a different prefix to avoid conflicts with other bots in the channel.

### At startup

Set `COMMAND_PREFIX` in your `.env` file before starting the bot:

```env
COMMAND_PREFIX=?sx
```

### At runtime (moderators and broadcaster only)

Use the `setprefix` command in Twitch chat:

```text
!sx setprefix ?sx
```

The change takes effect immediately for all subsequent messages in the session.
It is **not** persisted to the configuration file; the prefix resets to the value
in `.env` (or the default `!sx`) when the bot restarts.

Using a unique prefix is recommended if multiple bots share the same channel, so
that their commands do not interfere with each other.

## Stream Overlay

Streamantix includes a lightweight web overlay that can be added as a **Browser Source** in OBS Studio.
It displays live game information: best guess, last guess, attempt count, top-10 leaderboard, game status, and more.

### How to start the overlay

1. Enable the overlay in your `.env` file:

   ```env
   OVERLAY_ENABLED=true
   OVERLAY_PORT=8080   # optional, 8080 is the default
   ```

2. Start the bot as usual:

   ```bash
   poetry run python main.py
   ```

   The overlay server starts automatically alongside the bot on the configured port.

### OBS configuration

1. In OBS, add a new **Browser Source**.
2. Set the URL to:

   ```text
   http://localhost:8080/overlay
   ```

   If the bot is running on a different machine, replace `localhost` with the host's IP address and make sure port `8080` is reachable from the OBS machine.

3. Recommended browser source settings:
   - **Width**: 320 px
   - **Height**: 500 px
   - **Custom CSS**: `body { background: transparent; }` (already set by the overlay)
   - Enable **"Refresh browser when scene becomes active"** for reliability.

### Environment variables

| Variable          | Description                                      | Default  |
|-------------------|--------------------------------------------------|----------|
| `OVERLAY_ENABLED` | Set to `true` to start the overlay server        | `false`  |
| `OVERLAY_PORT`    | TCP port for the overlay HTTP/WebSocket server   | `8080`   |

### Network tips

- The overlay uses a WebSocket connection (`ws://<host>:<port>/ws`) for real-time updates.
- If OBS is on the same machine as the bot, use `localhost`.
- If running across machines, ensure the firewall allows inbound TCP on `OVERLAY_PORT`.
- The overlay page auto-reconnects every 3 seconds if the WebSocket drops.

## Running

```bash
poetry run python main.py
```

## Docker Deployment

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/) v2 (included with Docker Desktop)

### Build the image

```bash
docker build -t streamantix .
```

### Run with `docker run`

Create a `.env` file from the example (see [Setup](#setup)), then:

```bash
docker run --rm \
  --env-file .env \
  -v "$(pwd)/models:/app/models" \
  -v "$(pwd)/.secrets:/app/.secrets" \
  -p 4343:4343 \
  -p 8080:8080 \
  streamantix
```

- The first `-v` flag mounts a local `models/` directory into the container so the
  Word2Vec model is downloaded once and persisted across restarts.
- The second `-v` flag mounts `.secrets/` so OAuth tokens are persisted across restarts.
- The `-p 4343:4343` flag exposes the OAuth callback server (required for the first-time login flow).
- The `-p 8080:8080` flag is only necessary when `OVERLAY_ENABLED=true`.
- On the first run the model (~1 GB) is downloaded automatically. Subsequent
  starts skip the download if the file is already present in the mounted volume.

### First-time OAuth login inside Docker

When using the OAuth Authorization Code flow, the bot needs to complete an
interactive browser-based login on the first run. Use `docker compose run` with
the `--service-ports` flag so that port 4343 is accessible from your host:

```bash
docker compose run --service-ports streamantix python main.py auth-login
```

This starts a temporary local HTTP server inside the container on port 4343,
which is forwarded to your host. Open the printed authorization URL in your
browser, click **Authorize**, and the tokens will be saved to
`.secrets/twitch_tokens.json` on the host (via the mounted volume).

After the first login, start the bot normally:

```bash
docker compose up
```

### Run with Docker Compose

```bash
docker compose up
```

Docker Compose reads your `.env` file automatically, mounts `./models` and `./.secrets`
as persistent volumes, exposes the overlay port (default `8080`), and the OAuth
callback port (default `4343`).

To rebuild the image after code changes:

```bash
docker compose up --build
```

To run in the background:

```bash
docker compose up -d
docker compose logs -f   # stream logs
docker compose down      # stop and remove the container
```

### Persistent storage

The container writes the Word2Vec model to `/app/models` and OAuth tokens to
`/app/.secrets` inside the container. Mount host directories at those paths so
data survives container restarts:

```bash
# Named Docker volumes (recommended for production)
docker volume create streamantix-models
docker volume create streamantix-secrets
docker run --rm \
  --env-file .env \
  -v streamantix-models:/app/models \
  -v streamantix-secrets:/app/.secrets \
  streamantix
```

With Docker Compose the `./models` and `./.secrets` bind-mounts in `compose.yaml`
serve the same purpose for local development.

### Environment variables

All variables are documented in `.env.example`. The table below summarises the
most important ones:

| Variable               | Description                                               | Default |
|------------------------|-----------------------------------------------------------|---------|
| `TWITCH_TOKEN`         | Manual OAuth token (`oauth:…`) — optional if using OAuth flow | —   |
| `TWITCH_CHANNEL`       | Twitch channel name to join — **required**                | —       |
| `TWITCH_CLIENT_ID`     | Twitch app client ID (OAuth flow)                         | —       |
| `TWITCH_CLIENT_SECRET` | Twitch app client secret (OAuth flow)                     | —       |
| `TWITCH_REDIRECT_URI`  | OAuth redirect URI — set to `http://localhost:4343/callback` for local Docker | `http://localhost:4343/callback` |
| `TWITCH_SCOPES`        | Space-separated OAuth scopes                                              | `chat:read chat:edit` |
| `TWITCH_TOKEN_PATH`    | Path to the JSON token storage file inside the container                  | `.secrets/twitch_tokens.json` |
| `COMMAND_PREFIX`       | Prefix for bot commands                                                   | `!sx`   |
| `COOLDOWN`             | Cooldown between guesses (seconds)                                        | `5`     |
| `DIFFICULTY`           | Game difficulty (`easy` / `hard`)                                         | `easy`  |
| `MODEL_PATH`           | Path to the Word2Vec binary model inside the container                    | `models/frWac_no_postag_no_phrase_700_skip_cut50.bin` |
| `OVERLAY_ENABLED`      | Set to `true` to start the web overlay server                             | `false` |
| `OVERLAY_PORT`         | TCP port for the overlay HTTP/WebSocket server                            | `8080`  |
| `OAUTH_CALLBACK_PORT`  | Host-side port mapped to the container's OAuth callback server (port 4343) | `4343` |

### Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Container exits immediately with *"Required environment variable … is not set"* | `.env` file not passed or incomplete | Add `--env-file .env` to `docker run`, or verify all required variables in `compose.yaml` |
| Model download fails / times out | No internet access from the container | Ensure outbound HTTPS is allowed, or pre-download the model and place it in the mounted `models/` directory |
| Overlay not reachable from OBS | Port not published | Add `-p 8080:8080` to `docker run` or check the port mapping in `compose.yaml`; check firewall rules |
| OAuth callback not reachable | Port 4343 not published | Add `-p 4343:4343` to `docker run`, or set `OAUTH_CALLBACK_PORT` in your `.env` to customise the host port used by both `docker compose up` and `docker compose run --service-ports` |
| Permission denied writing to `models/` or `.secrets/` | Volume mounted as read-only or wrong ownership | Ensure the host directories are writable by UID 1000 (`chown -R 1000:1000 ./models ./.secrets`) |

## Project Structure

```text
streamantix/
├── auth/              # Twitch OAuth Authorization Code flow
│   └── twitch_auth.py # TokenManager: login, refresh, storage
├── bot/               # Twitch bot integration
│   ├── bot.py         # Bot definition and commands
│   └── cooldown.py    # Per-user cooldown logic
├── game/              # Game logic
│   ├── engine.py      # SemanticEngine (Word2Vec) and GameEngine (state/scoring)
│   └── word_utils.py  # Word loading, cleaning, and normalisation utilities
├── overlay/           # Web overlay for OBS
│   ├── server.py      # Starlette WebSocket + HTTP server
│   ├── state.py       # Game-state serialisation for the overlay
│   └── static/
│       └── index.html # OBS browser-source overlay page
├── data/              # Curated French word lists used as target words
│   ├── interest_words_f.txt  # Easy (facile) word list
│   └── interest_words_d.txt  # Hard (difficile) word list
├── models/            # Word embedding models (not versioned)
├── tests/             # Test suite
├── config.py          # Configuration loaded from environment
├── download_model.py  # Helper to download the embedding model
└── main.py            # Entry point
```

## License

AGPL-3.0-or-later
