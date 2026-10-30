# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Ask the Codex app server for account facts, through the JSON-RPC protocol the Codex CLI itself speaks.

  codex_account.py <method> [<method> ...]    e.g. account/read account/rateLimits/read account/usage/read
  codex_account.py --methods                  every account method the installed Codex protocol defines

Only methods whose name ends in `/read` run: the protocol also has methods that spend a reset credit or send
an e-mail, and none of those may ever run from here. Identities (e-mail, account, user and organization ids,
workspace routing) are dropped from the output, so nothing personal leaves the machine's state folder.
"""

import json
import re
import select
import subprocess
import sys
import tempfile
import time
from pathlib import Path

IDENTITY = re.compile(r"(email|accountid|userid|orgid|organization|workspacerouting)", re.IGNORECASE)


def redact(value):
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items() if not IDENTITY.search(key) and key != "id"}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def methods() -> list[str]:
    with tempfile.TemporaryDirectory() as out:
        subprocess.run(["codex", "app-server", "generate-json-schema", "--out", out], check=True, capture_output=True, timeout=60)
        text = "".join(path.read_text() for path in Path(out).glob("*.json"))
    return sorted(set(re.findall(r'"(account/[A-Za-z/]+)"', text)))


def call(names: list[str]) -> dict:
    server = subprocess.Popen(["codex", "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

    def send(message: dict) -> None:
        server.stdin.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
        server.stdin.flush()

    def answer(request_id: int, seconds: float = 30) -> dict | None:
        end = time.time() + seconds
        while time.time() < end:
            if select.select([server.stdout], [], [], 1)[0]:
                line = server.stdout.readline()
                if not line:
                    return None
                message = json.loads(line)
                if message.get("id") == request_id:
                    return message
        return None

    try:
        send({"id": 0, "method": "initialize", "params": {"clientInfo": {"name": "ai-capacity", "version": "1"}}})
        if not answer(0):
            return {"error": "the Codex app server did not answer initialize"}
        send({"method": "initialized"})
        results = {}
        for index, name in enumerate(names, start=1):
            # A request sent right after `initialized` sometimes goes unanswered; asking again gets the answer.
            for request_id in (index * 2 - 1, index * 2):
                send({"id": request_id, "method": name, "params": {}})
                if reply := answer(request_id, seconds=15):
                    break
            else:
                reply = {"error": "no answer"}
            results[name] = redact(reply.get("result")) if "result" in reply else {"error": reply.get("error")}
        return results
    finally:
        server.terminate()


def main() -> None:
    args = sys.argv[1:]
    if args == ["--methods"]:
        print(json.dumps(methods(), indent=2))
        return
    if not args or any(not name.endswith("/read") for name in args):
        sys.exit("usage: codex_account.py <method>/read ... | --methods   (only */read methods run)")
    print(json.dumps(call(args), indent=2))


if __name__ == "__main__":
    main()
