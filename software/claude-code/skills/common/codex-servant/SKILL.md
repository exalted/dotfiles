---
name: codex-servant
description: Use the Codex CLI (OpenAI's coding agent, on its own quota) as a stateless helper that gets all its context from Claude, never from its own config, memories, hooks or plugins. Use whenever you want codex to review, give a second opinion, implement a well-specified part, or challenge a fix, to save Claude quota or get an independent read; and for "/codex-servant refresh" or when its recipe may be out of date.
argument-hint: "[refresh]"
---

# Codex as a servant

Codex runs with model, effort and sandbox chosen per role in `scripts/roles.json`, never from Codex's own
config or defaults. It loads no `config.toml`, rules, AGENTS.md, memories, hooks, plugins, skills, apps or
MCP servers, and it saves no session. Everything it knows comes from the prompt you give it.

## Call it

```bash
uv run --quiet --no-project --script ~/.claude/skills/codex-servant/scripts/codex_exec.py run \
  --role <role> --cd <directory> --prompt-file <file> [--schema <json schema file>] [--out <file>] \
  [--network] [--add-dir <dir>] [--mcp context7]
```

It prints one JSON object: `status` is `ok` (the answer is in `last_message_file`), `unavailable` (codex hit
a usage or rate limit; the script answers `unavailable` without calling codex for 10 minutes), `timeout` or
`error`. On anything but `ok`, do the work yourself and check back later; never block on codex.

| Role | Model | Effort | Sandbox | Use it for |
|---|---|---|---|---|
| `probe` | gpt-6-astra | low | read-only | "is codex up?" |
| `opinion` | gpt-6-astra | medium | read-only | a quick independent verdict (is this story workable?) |
| `plan-review` | gpt-6.1-sol | high | read-only | an outside read of a plan or design |
| `review` | gpt-6.1-sol | xhigh | read-only | adversarial review of a diff |
| `challenge` | gpt-6.1-sol | xhigh | read-only | does this fix close the finding, what could it break |
| `implement` | gpt-6.1-sol | high | workspace-write | a well-specified part with a test to pass |
| `implement-retry` | gpt-6.1-sol | max | workspace-write | a second attempt at a hard part |

`ultra` effort is never used: it delegates on its own, beyond what a caller can bound.

Write prompts as briefs for a capable engineer who knows nothing: the goal, the files, the example to follow,
the constraints, what "done" means, and what not to touch. With `--schema`, give a JSON schema whose every
property is required and `additionalProperties` false; the answer is then that JSON.

`--network` lets a write role reach the network (installs); the night shift never passes it, so a delegate
cannot push or call out. `--mcp context7` adds the context7 docs server for
that call only (it starts through `npx`); nothing is written to Codex's config. Add other MCP servers only to
`roles.json`'s `mcp` table, and only battle-tested ones.

Treat codex's output like any other unreviewed contribution: read the diff, run the tests, and keep only
what holds.

## refresh

Codex moves fast, so this recipe goes stale. Run this when the user asks, when `doctor` fails, or when
`roles.json`'s `last_verified` is older than 30 days (tell the user then):

1. `uv run --quiet --no-project --script ~/.claude/skills/codex-servant/scripts/codex_exec.py doctor`: it
   checks every flag and feature the recipe uses against the installed CLI, lists the models this login sees,
   and records substitutes for missing models.
2. Read `codex --version`, `codex exec --help`, `codex features list`, and the model list in
   `~/.codex/models_cache.json` (or a CLI command that lists models, if one exists now). Look for: new flags
   that isolate better or replace one in `isolation`; features that load or save state and should be in
   `disable`; models newer or better suited than the ones in `roles`; changed effort levels.
3. Update `scripts/roles.json` (and the table above) with what changed, set `last_verified` to today and
   `codex_version` to the installed version, and run `doctor` and a `probe` again.
4. Say in a few lines what changed and why. This skill lives in the public dotfiles repo: keep it generic.
