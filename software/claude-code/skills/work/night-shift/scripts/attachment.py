#!/usr/bin/env -S uv run --quiet --no-project --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Download one Jira attachment from the short-lived URL the Atlassian MCP's downloadJiraIssueAttachment returns.

  attachment.py <KEY> <download url> <file name>

The picker never runs curl itself: this accepts only Atlassian's media host, writes only into the story's
dossier under NIGHT_SHIFT_RUN_DIR, and caps each file at 5 MB and each story's attachments at 20 MB.
Prints JSON: {"saved": <path>, "bytes": n} or {"skipped": <name>, "why": "..."}.
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ALLOWED_HOST = "api.media.atlassian.com"
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_BYTES = 20 * 1024 * 1024


def main() -> None:
    if len(sys.argv) != 4 or not re.match(r"^[A-Z][A-Z0-9]+-\d+$", sys.argv[1]):
        sys.exit("usage: attachment.py <KEY> <download url> <file name>")
    key, url, name = sys.argv[1:]
    run_dir = os.environ.get("NIGHT_SHIFT_RUN_DIR")
    if not run_dir:
        sys.exit("attachment.py: NIGHT_SHIFT_RUN_DIR is not set")
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname != ALLOWED_HOST:
        sys.exit(f"attachment.py: only https://{ALLOWED_HOST} URLs are accepted")
    dest_dir = Path(run_dir) / key / "dossier" / "attachments"
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe = (re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "attachment")[:120]
    used = sum(path.stat().st_size for path in dest_dir.iterdir() if path.is_file())
    with urllib.request.urlopen(url, timeout=60) as response:
        body = response.read(MAX_FILE_BYTES + 1)
    if len(body) > MAX_FILE_BYTES or used + len(body) > MAX_TOTAL_BYTES:
        print(json.dumps({"skipped": name, "why": "over the size cap"}))
        return
    path = dest_dir / safe
    path.write_bytes(body)
    print(json.dumps({"saved": str(path), "bytes": len(body)}))


if __name__ == "__main__":
    main()
