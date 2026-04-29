"""Tests for game.word_utils — word cleaning/normalisation and word-list loading."""

import pathlib
import tempfile

import pytest

from game.word_utils import build_cleaned_key_map, clean_word, load_word_list


class TestCleanWord:
    def test_lowercase(self):
        assert clean_word("BONJOUR") == "bonjour"

    def test_strip_whitespace(self):
        assert clean_word("  chat  ") == "chat"

    def test_strip_punctuation(self):
        assert clean_word("chat!") == "chat"

    def test_apostrophe_keeps_last_token(self):
        """'l'eau' should resolve to 'eau' (the meaningful token)."""
        assert clean_word("l'eau") == "eau"

    def test_curly_apostrophe(self):
        """Unicode right-single-quotation mark should be treated as apostrophe."""
        assert clean_word("l\u2019eau") == "eau"

    def test_accented_characters_preserved(self):
        """French accented letters must not be stripped."""
        assert clean_word("forêt") == "forêt"
        assert clean_word("château") == "château"

    def test_already_clean(self):
        assert clean_word("maison") == "maison"

    def test_hyphen_removed(self):
        """Hyphens are punctuation and should be removed."""
        assert clean_word("arc-en-ciel") == "arcenciel"

    def test_empty_string(self):
        assert clean_word("") == ""

    def test_only_punctuation(self):
        assert clean_word("!!!") == ""

    def test_mixed_case_with_accent(self):
        assert clean_word("Étoile") == "étoile"


class TestBuildCleanedKeyMap:
    def test_basic_key_included(self):
        key_to_index = {"maison_NOUN": 0}
        result = build_cleaned_key_map(key_to_index)
        assert "maison" in result
        assert result["maison"] == "maison_NOUN"

    def test_hyphenated_key(self):
        key_to_index = {"arc-en-ciel": 0}
        result = build_cleaned_key_map(key_to_index)
        assert "arc" in result
        assert result["arc"] == "arc-en-ciel"

    def test_apostrophe_key_excluded(self):
        key_to_index = {"l'eau": 0}
        result = build_cleaned_key_map(key_to_index)
        assert "l'eau" not in result

    def test_non_alnum_key_excluded(self):
        key_to_index = {"hello-world": 0, "foo!": 1}
        result = build_cleaned_key_map(key_to_index)
        # "hello" is alnum (first token of "hello-world"), so it should be present
        # "foo!" is not alnum after splitting (contains "!"), so "foo" must NOT appear
        assert "hello" in result
        assert "foo" not in result

    def test_first_occurrence_wins(self):
        """When two original keys clean to the same string, the first wins."""
        # dict preserves insertion order in Python 3.7+
        key_to_index = {"chat_NOUN": 0, "chat_ADJ": 1}
        result = build_cleaned_key_map(key_to_index)
        assert result["chat"] == "chat_NOUN"

    def test_empty_vocabulary(self):
        assert build_cleaned_key_map({}) == {}


class TestLoadWordList:
    def test_loads_words(self, tmp_path):
        f = tmp_path / "words.txt"
        f.write_text("arbre\nchat\nmaison\n", encoding="utf-8")
        assert load_word_list(f) == ["arbre", "chat", "maison"]

    def test_ignores_comments(self, tmp_path):
        f = tmp_path / "words.txt"
        f.write_text("# comment\narbre\n", encoding="utf-8")
        assert load_word_list(f) == ["arbre"]

    def test_ignores_blank_lines(self, tmp_path):
        f = tmp_path / "words.txt"
        f.write_text("arbre\n\nchat\n", encoding="utf-8")
        assert load_word_list(f) == ["arbre", "chat"]

    def test_utf8_accents(self, tmp_path):
        f = tmp_path / "words.txt"
        f.write_text("forêt\nchâteau\n", encoding="utf-8")
        result = load_word_list(f)
        assert "forêt" in result
        assert "château" in result
