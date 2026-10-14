#!/usr/bin/python3
"""Make Claude run the original commands, never the shell's aliases and functions.

Claude's Bash tool runs in a shell initialized from the user's profile, so a bare
`git` or `grep` runs a personal wrapper whose extra flags and side effects Claude
does not expect. Instructions alone get skipped, so this hook enforces them:

  refresh  (SessionStart) caches every alias and function that hides a real
           builtin or executable, as read from an interactive login bash.
  check    (PreToolUse on Bash) denies a command that calls a cached name at a
           command position without the `command` prefix.

Runs on the system python, without uv, because it runs before every Bash call.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from shell_commands import (
    COMMAND_PREFIX_KEYWORDS,
    COMMAND_SEPARATORS,
    strip_heredoc_bodies,
    tokenize,
)

CACHE_PATH = (
    Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    / "claude-code"
    / "shadowing-wrappers.json"
)
DEFINITION_MAX_LINES = 12
FIELD_SEPARATOR = "\x1f"
RECORD_SEPARATOR = "\x1e"

# Prints name, kind and definition of each alias or function that hides a builtin or executable.
# Forks only for the few matches: a fork per function took seconds with nvm's ~900 functions.
LIST_WRAPPERS_SCRIPT = r"""
declare -A builtins
for name in $(compgen -b); do builtins[$name]=1; done
hides_original() { [[ -n ${builtins[$1]:-} ]] || type -P "$1" >/dev/null; }
for name in "${!BASH_ALIASES[@]}"; do
  hides_original "$name" && printf '%s\x1falias\x1f%s\x1e' "$name" "alias $name='${BASH_ALIASES[$name]}'"
done
for name in $(compgen -A function); do
  hides_original "$name" && printf '%s\x1ffunction\x1f%s\x1e' "$name" "$(declare -f "$name")"
done
"""

FLAG_GUIDANCE = " ".join(
    [
        "Run the command again with each name prefixed by `command`.",
        "From each wrapper, keep a flag only if it is a sensible default that matches the user's",
        "preferences, for example one that makes a failure stop.",
        "Drop flags that change the output or behavior in ways you would not expect.",
    ]
)


Wrappers = dict[str, dict[str, str]]


def list_shadowing_wrappers() -> Wrappers:
    completed = subprocess.run(
        ["bash", "-lic", LIST_WRAPPERS_SCRIPT],
        capture_output=True,
        text=True,
        timeout=20,
        stdin=subprocess.DEVNULL,
    )
    wrappers: Wrappers = {}
    for record in completed.stdout.split(RECORD_SEPARATOR):
        fields = record.split(FIELD_SEPARATOR)
        if len(fields) == 3:
            name, kind, definition = fields
            wrappers[name.strip()] = {
                "kind": kind,
                "definition": "\n".join(definition.splitlines()[:DEFINITION_MAX_LINES]),
            }
    return wrappers


def refresh_cache() -> Wrappers:
    wrappers = list_shadowing_wrappers()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = CACHE_PATH.with_suffix(f".{os.getpid()}.tmp")
    temporary_path.write_text(json.dumps(wrappers, indent=2, sort_keys=True))
    temporary_path.replace(CACHE_PATH)
    return wrappers


def load_cache() -> Wrappers:
    try:
        return json.loads(CACHE_PATH.read_text())
    except (OSError, ValueError):
        return refresh_cache()


def called_names(command_line: str) -> list[str]:
    """Return every word that bash would run as a command, in order."""
    try:
        tokens = tokenize(strip_heredoc_bodies(command_line))
    except ValueError:
        return []
    names: list[str | None] = []
    at_command_position = True
    for token in tokens:
        if "$(" in token:
            for substitution in token.split("$(")[1:]:
                names.extend(called_names(substitution))
        if token in COMMAND_SEPARATORS:
            at_command_position = True
        elif at_command_position:
            if token in COMMAND_PREFIX_KEYWORDS or (
                "=" in token and not token.startswith("=")
            ):
                pass
            elif token in ("command", "builtin"):
                at_command_position = False
                names.append(None)
            else:
                names.append(token)
                at_command_position = False
    return [name for name in names if name is not None]


def deny(reason: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )


def describe(name: str, wrapper: dict[str, str]) -> str:
    return f"- `{name}` is a shell {wrapper['kind']}. Use `command {name}`. Its definition:\n{wrapper['definition']}"


def check(hook_input: dict[str, Any]) -> None:
    if hook_input.get("tool_name") != "Bash":
        return
    wrappers = load_cache()
    offending: list[str] = []
    for name in called_names(hook_input.get("tool_input", {}).get("command", "")):
        if name in wrappers and name not in offending:
            offending.append(name)
    if offending:
        deny(
            "\n".join(
                [
                    "These names run the user's shell wrappers, not the original commands:",
                    *(describe(name, wrappers[name]) for name in offending),
                    "",
                    FLAG_GUIDANCE,
                ]
            )
        )


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "refresh":
        refresh_cache()
    elif mode == "check":
        check(json.load(sys.stdin))
    else:
        sys.exit(f"usage: {Path(sys.argv[0]).name} refresh|check")


if __name__ == "__main__":
    main()
