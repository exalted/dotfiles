# How to get each fact

The first `methods.md` of a machine starts as a copy of this file. The refresh re-learns every route, keeps
`methods.md` current in the state folder and never edits this seed. `<scripts>` is this skill's `scripts/`.

| Fact | Route | Checks that it still works | Last verified |
|---|---|---|---|
| Claude plan, sign-in method, provider | `uv run --quiet --no-project --script <scripts>/claude_reports.py auth` (`claude auth status --json`: `subscriptionType`, `authMethod`, `apiProvider`) | JSON with `subscriptionType` | 2026-10-30 |
| Claude usage windows, resets, per-model weekly windows, usage advice | `claude_reports.py /usage` (local command, no model turn) | text with "Current session" and "Current week" lines | 2026-10-30 |
| Claude live utilization and overage status | `rate_limit_event` in `claude -p "Reply with OK." --model haiku --output-format stream-json --verbose --max-turns 1` | `unifiedWindows` with `five_hour` and `seven_day` | 2026-10-30 |
| Claude model aliases | `claude_reports.py /model` (local command) | an "Available:" list | 2026-10-30 |
| What an alias resolves to | `model` in the `system/init` event of a stream-json run with `--model <alias>` | a full model id | 2026-10-30 |
| Claude's strongest model | the `best` alias in the Claude Code docs (model-config, "Model aliases") and what it resolves to | docs row for `best` | 2026-10-30 |
| Claude default effort per model | Claude Code docs, model-config, "Adjust effort level": the model's default effort | a sentence naming the defaults | 2026-10-30 |
| Claude usage credits | `claude_reports.py /usage-credits` (local command) | text about usage credits | 2026-10-30 |
| Codex plan and sign-in | `uv run --quiet --no-project --script <scripts>/codex_account.py account/read` (Codex app server) | `account.planType` | 2026-10-30 |
| Codex usage windows, credits, free resets | `codex_account.py account/rateLimits/read` | `rateLimits.primary` and `secondary` with `usedPercent` | 2026-10-30 |
| Codex token use per day | `codex_account.py account/usage/read` | `dailyUsageBuckets` | 2026-10-30 |
| Codex account methods available | `codex_account.py --methods` | a list of `account/...` names | 2026-10-30 |
| Codex models and default reasoning levels | `codex debug models` (raw catalog JSON) | models with a slug and a default reasoning level | 2026-10-30 |
| Night-shift cost and outcome per session kind and model | `~/.local/state/night-shift/ledger.json`, knobs in `~/.config/dotfiles/night-shift/knobs.json` | entries with points per kind | 2026-10-30 |
| Model news and effort guidance | Claude Code docs (`https://code.claude.com/docs/en/model-config.md`), the Claude Code changelog, OpenAI's Codex docs and changelog | pages load | 2026-10-30 |

Where to look when a route breaks: the CLI's `--help` and each subcommand's `--help`; `/help` in a
`claude -p` run for local commands; the Claude Code changelog; `codex app-server generate-json-schema` for
the protocol's methods; Codex's release notes; the CLIs' own folders (`~/.claude/`, `~/.codex/`).
