"""Utilities for loading and processing word lists."""

import pathlib


def load_word_list(path: str | pathlib.Path) -> list[str]:
    """Load a word list from a plain-text file (one word per line).

    Lines that are empty or start with ``#`` are ignored, allowing comment
    headers inside the word list files.

    Args:
        path: Path to the word list file.

    Returns:
        A list of stripped, non-empty, non-comment words.
    """
    p = pathlib.Path(path)
    words = []
    for line in p.read_text(encoding="utf-8").splitlines():
        word = line.strip()
        if word and not word.startswith("#"):
            words.append(word)
    return words
