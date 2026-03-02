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
   | `MODEL_PATH`     | Path to the Word2Vec binary model file   | `models/frWac_no_postag_no_phrase_700_skip_cut50.bin` |

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

## Testing

Run the full test suite:

```bash
poetry run pytest
```

Run with coverage report:

```bash
poetry run pytest --cov
```

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
│   ├── engine.py      # SemanticEngine (Word2Vec) and GameEngine (state/scoring)
│   └── word_utils.py  # Word loading, cleaning, and normalisation utilities
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
