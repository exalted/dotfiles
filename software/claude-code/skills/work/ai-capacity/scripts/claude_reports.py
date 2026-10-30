# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""What Claude Code reports about the account, without a model turn.

  claude_reports.py [<command> ...]    default: auth /usage /model /usage-credits

`auth` runs `claude auth status --json`; a slash command runs as `claude -p <command>`, which Claude Code
answers locally (it costs nothing). A command that is not local any more runs a one-turn model call capped at
one cent, and the output says it is not local, so the route can be re-learned. Identities (e-mail,
organization id and name) are dropped.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

IDENTITY = re.compile(r"(email|orgid|orgname|organization|accountuuid)", re.IGNORECASE)
STATE = Path.home() / ".local" / "state" / "ai-capacity"
QUIET = {"CLAUDE_TODO_HOOKS": "0", "ENABLE_CLAUDEAI_MCP_SERVERS": "false"}


def run(command: list[str]) -> subprocess.CompletedProcess:
    STATE.mkdir(parents=True, exist_ok=True)
    return subprocess.run(command, cwd=STATE, env={**os.environ, **QUIET}, capture_output=True, text=True, timeout=120)


def report(name: str) -> dict:
    if name == "auth":
        done = run(["claude", "auth", "status", "--json"])
        try:
            return {key: value for key, value in json.loads(done.stdout).items() if not IDENTITY.search(key)}
        except json.JSONDecodeError:
            return {"error": (done.stderr or done.stdout).strip()[-400:]}
    done = run(["claude", "-p", name, "--output-format", "json", "--max-turns", "1", "--max-budget-usd", "0.01", "--strict-mcp-config"])
    try:
        data = json.loads(done.stdout)
    except json.JSONDecodeError:
        return {"error": (done.stderr or done.stdout).strip()[-400:]}
    if not data.get("local_command"):
        return {"error": f"{name} is not a local command any more: it ran a model turn", "cost_usd": data.get("total_cost_usd")}
    return {"text": data.get("result", "")}


def main() -> None:
    names = sys.argv[1:] or ["auth", "/usage", "/model", "/usage-credits"]
    print(json.dumps({name: report(name) for name in names}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
