---
name: ai-capacity
description: What the user's Claude and Codex accounts give them right now — plans, models, usage windows, limits, credits and default efforts — kept current by a weekly refresh that first re-learns how to get each fact, and advice on models, efforts and allowances (advice only, never a change). Use when the user asks about their plan, quota, limits, usage, credits or which models they have, when another skill (the night shift, model-steward) needs those facts, and for "/ai-capacity refresh".
argument-hint: "[refresh]"
model: fable
effort: high
introspective: true
---

# AI capacity

Everything this skill learns stays on this machine, in `~/.local/state/ai-capacity/`. Nothing about the
user's accounts goes into the dotfiles repository, a commit, or a message to anyone.

| File | Holds |
|---|---|
| `methods.md` | how to get each fact today; starts as a copy of `methods.seed.md` beside this file |
| `capacity.json` | the latest facts, each with its route and time (shape below) |
| `history/<date>.json` | one copy of `capacity.json` per refresh |
| `advice.md` | the current advice, each item with its evidence |

The user reads it in the living "AI status" note in Obsidian: `scripts/status_note.py ai-capacity <file>`
rewrites this skill's section there. Its path is in `~/.config/dotfiles/ai-capacity/note`; if that file is
missing, say so and point at `note.example` beside this file.

Hard rules: read only. Never sign in or out, spend a reset credit, request credits or send anything. Never
print, store or pass on a token, an e-mail address, or an account, user or organization id; the helper scripts
drop them. Advice is advice: never change a setting, a knob or a skill.

## No argument: answer from what is known

Read `capacity.json` and `advice.md` and answer the question. Say how old the facts are. If they are older
than 8 days, or the question needs a fact they lack, run the refresh first.

## refresh

### 1. Re-learn the routes

Routes change: a command is renamed, a cache file moves, a CLI gains a usage command. So before collecting:

1. Copy `methods.seed.md` to `methods.md` in the state folder if it is not there yet.
2. Run each route in `methods.md` once and check its output against the row's check.
3. For a route that fails or looks different, find its replacement: the CLI's `--help` and its subcommands'
   help, the Claude Code docs and changelog, `codex_account.py --methods` and Codex's release notes, the CLIs'
   own folders. Prefer a route the CLI or its vendor offers over reading internal files.
4. Look for better routes too: a new local command, a new `account/.../read` method, a docs page that states
   a fact a route only implies.
5. Rewrite `methods.md`: every row with today's date when verified, and under it a short "Changed" list with
   the old route, the new one and the evidence.

### 2. Collect

Get every fact through the verified routes and write `capacity.json`:

```json
{
  "refreshed_at": "<ISO time>",
  "claude": {
    "plan": "team", "auth_method": "claude.ai",
    "windows": [{"name": "Current week (Fable)", "percent": 16, "resets": "<ISO time>"}],
    "overage": "allowed, not in use",
    "credits": "<what /usage-credits says>",
    "aliases": ["sonnet", "opus", "haiku", "fable", "best"],
    "resolved": {"fable": "claude-fable-5-1"},
    "default_effort": {"fable": "high", "opus": "medium"},
    "strongest": {"alias": "fable", "model": "claude-fable-5-1", "default_effort": "high", "evidence": "<docs line>"},
    "usage_advice": ["<Claude Code's own /usage suggestions>"]
  },
  "codex": {
    "plan": "team",
    "windows": [{"name": "5 hours", "percent": 0, "resets": "<ISO time>"}],
    "credits": {"has_credits": false, "balance": null}, "reset_credits": [{"title": "", "expires": "<ISO time>"}],
    "models": [{"slug": "", "default_reasoning": ""}],
    "daily_tokens": [{"date": "", "tokens": 0}]
  },
  "sources": {"<fact>": "<route>"}
}
```

`strongest` is the most capable Claude model the account can use, as a concrete alias, and that model's own
default effort from the docs (never the user's `modelSettings` override). `model-steward` relies on it: write
it only when both parts are verified, else leave it out and say why.

Copy the file to `history/<today>.json`.

### 3. Advise

Compare with the previous history file and read the night shift's ledger and knobs (see `methods.md`). Write
`advice.md`: what changed (a plan, a model, a limit, credits) and what the user could do about it. Examples
of advice that helps:

- a model or effort better suited to a night-shift session kind, from its measured cost per outcome;
- a higher or lower night allowance from how much of each 7-day window was left at reset;
- work worth moving to Codex while its windows have room, or a free Codex reset about to expire;
- Claude Code's own `/usage` suggestions that apply.

Only what the user should know or do: a change that affects them, or an action worth taking. Nothing about
how the refresh went, no facts that are merely current, no item that repeats last week's unless it is still
open and still matters. Fewer is better; none is a valid result.

Format: one top-level `- ` line per item, under about 25 words: the action or the news first, the reason after.
Its evidence goes on indented lines below it (`  - evidence: …`), which only `advice.md` keeps. The night
shift shows the top-level lines in each run note and in `/night-shift status`.

### 4. Tell the user

The AI status note says only what the user should know or do: the top-level advice lines, nothing else. No
heading of its own, no tables, no facts, no account of the refresh. With no advice, the section is the single
line "Nothing needs you." Write it to a file in the state folder and run
`status_note.py ai-capacity <that file>`. A route that broke and could not be re-learned is advice too: one
line saying which fact is missing.

End with a summary of a few lines for the job's log: routes re-learned, what changed, the advice.
