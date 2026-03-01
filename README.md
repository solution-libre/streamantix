# streamantix

Twitch chat bot to play a Cemantix-like semantic word guessing game.

Players guess a secret word by submitting words in chat. The bot uses word embeddings
(via Gensim) to score each guess based on its semantic similarity to the target word.

## Requirements

- Python 3.12+
- [Poetry](https://python-poetry.org/) for dependency management
- A Twitch account with an OAuth token

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

   | Variable         | Description                              | Default |
   |------------------|------------------------------------------|---------|
   | `TWITCH_TOKEN`   | Twitch OAuth token (`oauth:...`)         | —       |
   | `TWITCH_CHANNEL` | Twitch channel name to join              | —       |
   | `COMMAND_PREFIX` | Prefix for bot commands                  | `!sx`   |
   | `COOLDOWN`       | Cooldown between guesses (seconds)       | `5`     |
   | `DIFFICULTY`     | Game difficulty (`easy`=facile, `hard`=difficile) | `easy` |

3. **Download the word embedding model**

   ```bash
   poetry run python download_model.py
   ```

   This will download the required Gensim word2vec model into the `models/` directory
   (which is not versioned).

## Running

```bash
poetry run python main.py
```

## Project Structure

```
streamantix/
├── bot/               # Twitch bot integration
│   ├── bot.py         # Bot definition and commands
│   └── cooldown.py    # Per-user cooldown logic
├── game/              # Game logic
│   ├── engine.py      # Game state and scoring
│   └── word_utils.py  # Word loading and processing utilities
├── data/              # Word lists (versioned)
├── models/            # Word embedding models (not versioned)
├── tests/             # Test suite
├── config.py          # Configuration loaded from environment
├── download_model.py  # Helper to download the embedding model
└── main.py            # Entry point
```

## License

AGPL-3.0-or-later
