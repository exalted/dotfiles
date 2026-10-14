---
name: sync-gitlab-repos
description: Bring the local GitLab checkouts under ~/Developer level with origin using fast-forward only, skipping any repo with ongoing work. Use when the user asks to update, sync, pull, refresh, or catch up their repos / local checkouts / the cwd's from GitLab, or asks for this before starting other work. Accepts an optional root path argument (default ~/Developer). Returns a finished Markdown report; show it to the user verbatim, with nothing before or after it.
argument-hint: "[root]"
model: haiku
context: fork
background: false
---

# Sync GitLab repos

Run this one command, and no other command:

```bash
command bash "${CLAUDE_SKILL_DIR}/scripts/sync.sh" --apply $ARGUMENTS
```

The script does the whole job: it fetches every GitLab repo directly under the root, fast-forwards the ones that are behind with no ongoing work, checks that stash counts and dirty state are as before, and prints the report. It touches nothing when any fetch fails (exit 2), and it stops at a `stash pop` conflict without resolving it (exit 3).

Your final message is the script's output exactly as printed, whatever the exit code: no sentence before it, no recap after it.

## Hard rules

- Do not run git yourself, do not re-run the script, and do not act on the report. A branch moves only through the script's `merge --ff-only`.
- The report may end by offering to stash ongoing work and fast-forward. Only offer it; never perform it without the user's explicit go-ahead.
- If the report shows `❌ fetch failed`, do not try another way to authenticate. The report tells the user how to sign in again.
