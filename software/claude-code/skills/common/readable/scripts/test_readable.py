#!/usr/bin/python3
"""Tests for readable.py against a throwaway transcript.

Run:  /usr/bin/python3 -m unittest software/claude-code/skills/common/readable/scripts/test_readable.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import readable  # noqa: E402


def prompt(text: str) -> dict:
    return {"type": "user", "message": {"content": text}}


def tool_result() -> dict:
    return {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}}


def assistant(text: str, **extra: object) -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}, **extra}


class WordLimit(unittest.TestCase):
    def test_no_limit_for_a_short_reply(self) -> None:
        self.assertIsNone(readable.word_limit(39))

    def test_share_that_must_go_grows_with_the_length(self) -> None:
        shares = [1 - readable.word_limit(words) / words for words in (40, 100, 314, 1000, 5000)]
        self.assertEqual(shares, sorted(shares))

    def test_result_is_never_above_the_cap(self) -> None:
        self.assertEqual(readable.word_limit(314), 157)
        self.assertLess(readable.word_limit(1_000_000), readable.CAP_WORDS)


class SplitBlocks(unittest.TestCase):
    def test_code_and_tables_are_not_prose(self) -> None:
        text = "One two.\n```bash\nls -la\n```\nThree.\n| a | b |\n|---|---|\nFour."
        prose, blocks = readable.split_blocks(text)
        self.assertEqual(readable.word_count(prose), 4)
        self.assertEqual(blocks, ["```bash\nls -la\n```", "| a | b |\n|---|---|"])


class Replies(unittest.TestCase):
    def replies(self, entries: list) -> list:
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as file:
            file.write("\n".join(json.dumps(entry) for entry in entries))
        self.addCleanup(os.unlink, file.name)
        return readable.replies(file.name)

    def test_a_reply_is_the_last_text_of_a_finished_turn(self) -> None:
        found = self.replies(
            [
                prompt("first"),
                assistant("I will look."),
                tool_result(),
                assistant("First answer."),
                prompt("second"),
                assistant("Second answer."),
                prompt("/readable"),
                assistant("Text of the turn in progress."),
            ]
        )
        self.assertEqual(found, ["First answer.", "Second answer."])

    def test_injected_context_and_subagents_do_not_count(self) -> None:
        found = self.replies(
            [
                prompt("first"),
                assistant("Answer."),
                {**prompt("skill text"), "isMeta": True},
                assistant("Subagent text.", isSidechain=True),
                prompt("/readable"),
            ]
        )
        self.assertEqual(found, ["Answer."])


class Checks(unittest.TestCase):
    ORIGINAL = "word " * 100 + "For example, `git checkout` changes the file.\n```\nls\n```"

    def problems(self, draft: str) -> list:
        return [check.__name__ for check in readable.CHECKS if check(self.ORIGINAL, draft)]

    def test_a_good_draft_passes(self) -> None:
        self.assertEqual(self.problems("Short. For example, `git checkout`.\n```\nls\n```"), [])

    def test_too_long(self) -> None:
        self.assertIn("check_what_matters", self.problems("word " * 90 + "for example"))

    def test_lost_example(self) -> None:
        self.assertEqual(self.problems("Short."), ["check_examples"])

    def test_changed_code_block(self) -> None:
        draft = "Short, for example.\n```\nls -la\n```"
        self.assertEqual(self.problems(draft), ["check_blocks_verbatim"])

    def test_stat_line_is_not_part_of_the_draft(self) -> None:
        self.assertEqual(readable.without_stat_line("Text.\n\n_32% shorter (111 → 75 words)_"), "Text.\n")


if __name__ == "__main__":
    unittest.main()
