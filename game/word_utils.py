"""Utilities for loading and processing word lists."""

import pathlib


def load_word_list(path: str | pathlib.Path) -> list[str]:
    """Load a word list from a plain-text file (one word per line).

    Args:
        path: Path to the word list file.

    Returns:
        A list of stripped, non-empty words.
    """
    p = pathlib.Path(path)
    return [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
