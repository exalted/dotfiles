#!/usr/bin/python3
"""Give the exact word limit for an edit of an assistant reply, and check a draft against it.

The `readable` skill tells Claude how to edit a reply. A model counts words only
approximately, so this script does the parts that must be exact: it reads the reply from
the session transcript, calculates the limit, and checks the draft.

Each check belongs to one concern of the skill. To add a check, add a function to CHECKS.

Code blocks and tables are not in the word count.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Optional

CAP_WORDS = 314
MIN_WORDS_FOR_LIMIT = 40
# A list needs a lead-in line that the sentence it replaces did not have.
MAX_ADDED_WORDS = 10

WORD = re.compile(r"\S*\w\S*")
FENCE = re.compile(r"^\s*(```|~~~)")
TABLE_ROW = re.compile(r"^\s*\|")
EXAMPLE = re.compile(r"\b(for example|for instance|e\.g\.|examples?:|such as)", re.IGNORECASE)
STAT_LINE = re.compile(r"^_\d+% shorter \(.*\)_$|^_edited_$")


def split_blocks(text: str) -> tuple:
    """Return the prose, and the fenced code blocks and tables apart from it."""
    prose, blocks, current = [], [], []
    fence = None

    def close_block() -> None:
        blocks.append("\n".join(current).strip())
        current.clear()

    for line in text.split("\n"):
        marker = FENCE.match(line)
        if fence:
            current.append(line)
            if marker and marker.group(1) == fence:
                fence = None
                close_block()
        elif marker:
            if current:
                close_block()
            fence = marker.group(1)
            current.append(line)
        elif TABLE_ROW.match(line):
            current.append(line)
        else:
            if current:
                close_block()
            prose.append(line)
    if current:
        close_block()
    return "\n".join(prose), blocks


def word_count(prose: str) -> int:
    return len(WORD.findall(prose))


def word_limit(original_words: int) -> Optional[int]:
    """With n = words in the original and C = CAP_WORDS, allow n * C / (n + C) words.

    The share that must go, n / (n + C), grows with n, and the result can never be longer
    than C.
    """
    if original_words < MIN_WORDS_FOR_LIMIT:
        return None
    return original_words * CAP_WORDS // (original_words + CAP_WORDS)


def check_what_matters(original: str, draft: str) -> Optional[str]:
    limit = word_limit(word_count(split_blocks(original)[0]))
    words = word_count(split_blocks(draft)[0])
    if limit is None or words <= limit:
        return None
    return f"The draft has {words} words. The limit is {limit}. Delete the least important content."


def check_examples(original: str, draft: str) -> Optional[str]:
    if EXAMPLE.search(original) and not EXAMPLE.search(draft):
        return "The reply gives an example, and the draft has none. Put it back."
    return None


def check_blocks_verbatim(original: str, draft: str) -> Optional[str]:
    original_blocks = split_blocks(original)[1]
    changed = [block for block in split_blocks(draft)[1] if block not in original_blocks]
    if not changed:
        return None
    first_line = changed[0].split("\n")[0]
    return (
        f"{len(changed)} code block(s) or table(s) in the draft are not verbatim from the "
        f"reply, the first one starts with: {first_line}"
    )


def check_not_longer(original: str, draft: str) -> Optional[str]:
    original_words = word_count(split_blocks(original)[0])
    if word_count(split_blocks(draft)[0]) > original_words + MAX_ADDED_WORDS:
        return "The draft is longer than the reply."
    return None


CHECKS = (check_what_matters, check_examples, check_blocks_verbatim, check_not_longer)


def is_prompt(entry: dict) -> bool:
    """True for an entry that starts a turn, not for a tool result or injected context."""
    if entry.get("type") != "user" or entry.get("isMeta"):
        return False
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return True
    return isinstance(content, list) and any(
        isinstance(part, dict) and part.get("type") == "text" for part in content
    )


def assistant_text(entry: dict) -> str:
    if entry.get("type") != "assistant":
        return ""
    content = entry.get("message", {}).get("content")
    if not isinstance(content, list):
        return ""
    return "\n".join(
        part.get("text", "")
        for part in content
        if isinstance(part, dict) and part.get("type") == "text"
    ).strip()


def replies(transcript_path: str) -> list:
    """Return the last text of each finished turn, oldest first.

    The turn in progress is the one that runs this script, so it is not a reply.
    """
    finished, last_text = [], ""
    with open(transcript_path, encoding="utf-8", errors="replace") as file:
        for line in file:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not isinstance(entry, dict) or entry.get("isSidechain"):
                continue
            if is_prompt(entry):
                if last_text:
                    finished.append(last_text)
                last_text = ""
            else:
                last_text = assistant_text(entry) or last_text
    return finished


def transcript_path() -> str:
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    found = glob.glob(os.path.join(config_dir, "projects", "*", f"{session_id}.jsonl"))
    if not session_id or len(found) != 1:
        raise SystemExit(
            "Cannot find the transcript of this session. Write the reply to a file and "
            "pass it with --original-file."
        )
    return found[0]


def read_original(arguments: argparse.Namespace) -> str:
    if arguments.original_file:
        with open(arguments.original_file, encoding="utf-8") as file:
            return file.read()
    found = replies(transcript_path())
    if arguments.reply > len(found):
        raise SystemExit(f"This session has only {len(found)} finished replies.")
    return found[-arguments.reply]


def without_stat_line(draft: str) -> str:
    lines = draft.rstrip().split("\n")
    if lines and STAT_LINE.match(lines[-1].strip()):
        lines.pop()
    return "\n".join(lines)


def stat_line(original: str, draft: str) -> str:
    original_words = word_count(split_blocks(original)[0])
    if word_limit(original_words) is None:
        return "_edited_"
    words = word_count(split_blocks(draft)[0])
    saved = round(100 * (original_words - words) / original_words)
    return f"_{saved}% shorter ({original_words} → {words} words)_"


def limit_command(arguments: argparse.Namespace) -> int:
    original = read_original(arguments)
    prose, blocks = split_blocks(original)
    words = word_count(prose)
    limit = word_limit(words)
    first_line = next((line for line in original.split("\n") if line.strip()), "")
    print(f"Reply starts with: {first_line[:100]}")
    print(f"Words: {words}, plus {len(blocks)} code block(s) or table(s) that do not count")
    if limit is None:
        print(f"Limit: none, the reply has fewer than {MIN_WORDS_FOR_LIMIT} words. Do not make it longer.")
    else:
        print(f"Limit: {limit} words")
    return 0


def check_command(arguments: argparse.Namespace) -> int:
    original = read_original(arguments)
    if arguments.draft_file:
        with open(arguments.draft_file, encoding="utf-8") as file:
            draft = file.read()
    else:
        draft = sys.stdin.read()
    draft = without_stat_line(draft)
    problems = [problem for problem in (check(original, draft) for check in CHECKS) if problem]
    if problems:
        print("NOT OK")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("OK. End the edited reply with this line:")
    print(stat_line(original, draft))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    for name, handler in (("limit", limit_command), ("check", check_command)):
        command = commands.add_parser(name)
        command.set_defaults(handler=handler)
        command.add_argument("--reply", type=int, default=1, help="1 is the latest reply")
        command.add_argument("--original-file", help="read the reply from this file")
        if name == "check":
            command.add_argument("--draft-file", help="read the draft from this file, not stdin")
    arguments = parser.parse_args()
    if arguments.reply < 1:
        parser.error("--reply starts at 1")
    return arguments.handler(arguments)


if __name__ == "__main__":
    sys.exit(main())
