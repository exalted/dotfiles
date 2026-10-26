"""A dialog that stays on screen until the user answers it: for what only the user can fix, such as an
expired GitLab sign-in that stops `git fetch`.

One dialog at a time: while one is open, a new alert does not open a second. "Sync now" opens iTerm with
/sync-gitlab-repos in a new Claude Code session; a night run that waits for fresh checkouts sees the sync and
goes on by itself.
"""

import os
import subprocess
import time

from common import ALERT_FILE, read_json, write_json

SYNC_COMMAND = "cd ~/Developer && claude /sync-gitlab-repos; exec $SHELL -l"
DIALOG = """on run argv
    set answer to button returned of (display alert (item 1 of argv) message (item 2 of argv) as critical buttons {"Later", "Sync now"} default button "Sync now")
    if answer is "Sync now" then
        tell application "iTerm"
            activate
            create window with default profile command ("/bin/bash -lc " & quoted form of (item 3 of argv))
        end tell
    end if
end run
"""


def _open() -> bool:
    pid = int((read_json(ALERT_FILE, {}) or {}).get("pid") or 0)
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def show(title: str, message: str) -> bool:
    """Open the dialog unless one is already open; never waits for the answer."""
    if _open():
        return False
    process = subprocess.Popen(
        ["/usr/bin/osascript", "-e", DIALOG, title, message, SYNC_COMMAND],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    write_json(ALERT_FILE, {"pid": process.pid, "title": title, "message": message, "at": time.time()})
    return True


def stale_repos(problems: list[str], *, tonight: bool) -> bool:
    when = "The night shift is waiting for it now." if tonight else "Tonight's night shift needs it."
    message = (
        "Its checkouts cannot be refreshed from GitLab:\n\n" + "\n".join(f"• {problem}" for problem in problems)
        + f"\n\nSign in to GitLab in your browser (its SSO session expired), then run /sync-gitlab-repos. {when}"
    )
    return show("Night shift: sync your GitLab checkouts", message)
