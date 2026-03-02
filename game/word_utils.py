"""Utilities for loading and processing word lists."""

import pathlib
import re
import unicodedata


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


def clean_word(word: str) -> str:
    """Normalise a user-supplied word for model lookup.

    Applies the same transformations used when building the cleaned key map:
    lowercase, strip whitespace, drop punctuation (keeping alphanumeric
    characters and Unicode letters/digits such as accented French characters).

    Apostrophes are handled by keeping only the portion after the last
    apostrophe (e.g. ``"l'eau"`` → ``"eau"``).

    Args:
        word: Raw word as received from user input.

    Returns:
        The cleaned, normalised word.
    """
    word = word.strip().lower()
    # Keep only the last token when the word contains an apostrophe
    if "'" in word or "\u2019" in word:
        word = re.split(r"['\u2019]", word)[-1]
    # Remove characters that are not Unicode letters or digits
    word = "".join(ch for ch in word if unicodedata.category(ch)[0] in ("L", "N"))
    return word


def build_cleaned_key_map(key_to_index: dict) -> dict[str, str]:
    """Build a mapping from cleaned keys to original model vocabulary keys.

    Mirrors the ``create_cleaned_key_map`` logic from os-cemantix:

    1. Strip POS tags and compound suffixes (``word_TAG`` → ``word``,
       ``word-suffix`` → ``word``).
    2. Keep only purely alphanumeric entries.
    3. Exclude entries containing an apostrophe.

    Args:
        key_to_index: The ``key_to_index`` dict from a :class:`gensim.models.KeyedVectors`
            instance.

    Returns:
        A ``{clean_key: original_key}`` mapping where the first occurrence
        wins (i.e. earlier vocabulary entries take priority).
    """
    cleaned: dict[str, str] = {}
    for original_key in key_to_index:
        clean = original_key.split("_")[0].split("-")[0]
        if not clean.isalnum():
            continue
        if "'" in clean:
            continue
        if clean not in cleaned:
            cleaned[clean] = original_key
    return cleaned
