---
name: model-steward
description: Keep the scheduled job of every introspective skill (one that studies Claude Code, the tools or the accounts, marked `introspective: true`) on the strongest Claude model, at that model's own default effort, as ai-capacity last verified them, and commit the change. Use for /model-steward, after an ai-capacity refresh, or when the user asks which model the introspective skills and their jobs run on.
argument-hint: "[--commit]"
introspective: true
---

# Model steward

The rule, the user's: the scheduled job of an introspective skill (its weekly refresh) runs on the most
capable model available, at that model's own built-in default effort, never the user's `modelSettings`
override. An interactive lookup in the same skill runs on the session's model: pinning lookups to the
strongest model cost about a tenth of a week's usage for no gain.

```bash
uv run --quiet --no-project --script ~/.claude/skills/model-steward/scripts/steward.py [--commit]
```

- The strongest model and its default effort come from ai-capacity (`claude.strongest` in
  `~/.local/state/ai-capacity/capacity.json`). If that is missing, older than 14 days, or not verified, the
  script changes nothing and says why: run `/ai-capacity refresh` first.
- It sets `--model` and `--effort` on every `claude -p "/<skill> …"` line of the jobs in
  `software/claude-code/*.sh`, and removes `model:` and `effort:` from each introspective skill's frontmatter.
  Never add them back by hand: a skill's frontmatter applies to every lookup.
- Without `--commit` it only edits; tell the user what changed. With `--commit` it commits the changed files by
  pathspec, unless one of them had uncommitted changes before the run. It never pushes.

A new introspective skill joins by adding `introspective: true` to its frontmatter. This skill is marked too,
but runs no model itself: the script is all it needs.

The weekly ai-capacity job (`software/claude-code/ai-capacity-refresh.sh`) runs it with `--commit` after each
refresh.
