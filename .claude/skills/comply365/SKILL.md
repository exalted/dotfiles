---
name: comply365
description: Verify, extend and hand off this repo's work-project shell integration — software/comply365/SPEC.md, its Stop-hook verifier, and the manual sign-off ledger. Use when onboarding a newly cloned work repo, after running any repo's setup.sh, when a criterion fails, when adding shell behavior that needs a criterion, or when asked whether anything regressed.
---

# comply365 shell integration

Work repos in `~/Developer` expect shell behavior their own `setup.sh` installs
into rc files. `bin/dotfiles` regenerates `~/.bashrc` from scratch every run, so
anything appended from outside this repo is erased. `software/comply365/`
re-expresses those needs as dotfiles-owned fragments, `SPEC.md` says what
"working" means, and a `Stop` hook refuses to let a session end while any
automated criterion fails or any manual one is unconfirmed.

**The contract, and it matters: the projects' own setups install the tools; this
repo only wires configuration.** Never add a `brew` call to
`software/comply365/*.rb`.

## Pick the task

| Argument | Do this |
|---|---|
| *(none)* or `status` | [Status](#status) |
| `drift` | [After a repo's setup.sh ran](#after-a-repos-setupsh-ran) |
| `onboard <repo>` | [Onboarding a newly cloned work repo](#onboarding-a-newly-cloned-work-repo) |
| `check` | [Run the verifier](#run-the-verifier) |
| `sweep` | [Getting the manual criteria confirmed](#getting-the-manual-criteria-confirmed) |
| `criterion` | [Adding a criterion](#adding-a-criterion) |
| `fail <AC-id>` | [When a criterion fails](#when-a-criterion-fails) |

## Status

```bash
echo '{}' | .claude/hooks/comply365-spec-check.sh | python3 -m json.tool
```

`systemMessage` = everything passes. `decision: block` + `reason` = automated
failures and/or unconfirmed manual criteria. The hook self-gates: it does
nothing unless the session touched a watched path (see `WATCHED` in the script),
so silence in an unrelated session is correct.

Manual verdicts live in `.claude/comply365-manual-signoff.json` (gitignored, a
per-machine observation). Never delete it to "clean up" — that re-opens every
manual criterion.

## Run the verifier

```bash
echo '{}' | .claude/hooks/comply365-spec-check.sh          # gated, full output
.claude/tools/zsh-drift.sh                                 # exit 0 = no drift
```

## After a repo's setup.sh ran

Those scripts mutate startup files behind your back. Always:

```bash
cd ~/Developer/<repo> && ./setup/setup.sh    # or whatever it ships
cd ~/Developer/dotfiles && .claude/tools/zsh-drift.sh
```

- `TRANSIENT` — in `~/.bashrc`, already durable here. Erased on the next
  `bin/dotfiles` run and nothing is lost. No action.
- `MIRRORED` — zsh-only, Bash equivalent exists here. No action.
- `UNMIRRORED` — **the only lines needing a decision.** Continue below.

## Onboarding a newly cloned work repo

**Default answer: add nothing.** Walk this first.

1. `grep -rE 'bashrc|zshrc|zprofile|nvm|direnv|chpwd' <repo>/setup*/setup.sh` —
   does it write to an rc file or install a runtime manager?
2. Has `.envrc`? Covered by `comply365/cortex.bashrc` (direnv hook, every
   directory). One manual step per clone: `direnv allow` inside it.
3. Has `.nvmrc`? Covered by `comply365/web-safety.bashrc` — the hook walks up
   from `$PWD`, so it works for any repo. `web-cockpit` needed zero changes for
   exactly this reason. **Do not add a per-project copy of the hook.**
4. Git hooks with `#!/bin/zsh` or `env zsh`? Covered by `~/.zshenv`
   (`comply365/zsh.rb`).
5. Only if none of the above covers it: add `software/comply365/<project>.rb`
   (+ a `.bashrc` fragment if needed), register it in `profiles.rb` under
   `work`, `chmod +x` the `.rb`, then [add criteria](#adding-a-criterion).

The three mechanisms are **generic despite their per-project names**. Widening
one beats adding a fourth file.

Known gap, deliberately unsolved: hooks with `#!/bin/sh` or `#!/usr/bin/env sh`
(e.g. `web-cockpit`) get no startup file when a GUI app spawns them — `~/.zshenv`
is a zsh mechanism. If one fails from Sourcetree, that is the cause.

## Adding a criterion

Adding behavior means adding a criterion. A change that cannot be expressed as
one is a change nobody can verify later.

### `[auto]` — assert behavior, not the presence of a string

Add to `software/comply365/SPEC.md`, then a check in
`.claude/hooks/comply365-spec-check.sh` using the existing `check` helper:

```bash
some_command_or_probe
check AC-NN "what is broken, in terms of the consequence a human would notice"
```

`check` consumes `$?` from the immediately preceding command. Prefer a real
probe in a sandbox over a grep: the checks that caught actual regressions
compose `PROMPT_COMMAND` in a clean shell where nvm does not exist yet, drive
the nvm hook against a stub `nvm`, run the entry scripts twice against a
throwaway `$HOME`, and probe `bash` resolution under a stale `HOMEBREW_PREFIX`.
Grep-based checks mostly catch bookkeeping mistakes.

**Verify every new check in BOTH directions before believing it:**

```bash
# 1. break the thing deliberately
# 2. echo '{}' | .claude/hooks/comply365-spec-check.sh   -> must FAIL, naming it
# 3. restore
# 4. echo '{}' | .claude/hooks/comply365-spec-check.sh   -> must PASS
```

A check that cannot fail is worse than no check: it reads as coverage. Two in
this repo were vacuous when first written — one tested an exit status where the
tool exits 0 and complains on stderr, one captured stderr where this repo's
`warn` prints to **stdout** (`src/common.rb` overrides it with `puts`).

### `[eyes]` — needs a human

Prose entry in `SPEC.md`, plus a line in its `manual-checks` block:

```
AC-NN|<comma-separated files the verdict depends on>|<exact steps and what to expect>
```

- The dependency list must name the files that **implement** the behavior, not
  the ones that look related. Two of the five defects a reviewer found here were
  dependency lists pointing at the wrong file, which made those sign-offs
  effectively permanent.
- Write the steps so they cannot be misread. `cd X && nvm current` reads one
  step behind, because the hook runs from `PROMPT_COMMAND` after the command
  line finishes — that produced a false failure until the criterion spelled out
  "separate commands".
- Say what output *proves* it, so the user can stop early. AC-23 is satisfied by
  one line of hook stderr, not by waiting out `pnpm test`.

### Wire the paths

If the behavior lives in a file not already watched, add it to **both** scripts
— `WATCHED` (the gate) in `comply365-spec-check.sh`, and the digest path list in
`comply365-spec-check.sh` *and* `comply365-signoff.sh`. They must stay
identical or a fresh sign-off reads as stale immediately:

```bash
diff <(grep -o "ls-files.*profiles.rb" .claude/hooks/comply365-spec-check.sh) \
     <(grep -o "ls-files.*profiles.rb" .claude/hooks/comply365-signoff.sh) && echo "in sync"
```

Paths missed once here, each with a real consequence: `software/watch/bashrc`
and `software/git/bin/git-hist` (AC-28's actual mechanism), `profiles.rb` (it
decides whether a fragment is sourced *at all* — how the `watch` alias went
missing for the whole `work` profile), `software/iterm2/bashrc`.

## Getting the manual criteria confirmed

`[eyes]` criteria are **failing until a human says otherwise**. Ask, wait, then
record. Never assume, and never infer one criterion from another criterion's
steps.

```bash
.claude/hooks/comply365-signoff.sh <AC-id> pass    # or fail
```

A verdict is stored with a digest of the batch's **code** (tracked and
untracked, sorted). Any code change expires every manual verdict — that is
intended. `SPEC.md` is deliberately outside the digest so fixing a criterion's
wording does not force a full re-run; the tradeoff is that *tightening* a
criterion means revoking its sign-off by hand.

**Carrying a verdict forward** across a change that provably cannot affect it is
legitimate — but say so explicitly, name the reasoning, and offer to revoke. Do
not do it silently.

### The sweep, as few sittings as possible

Group the asks. This is the shape that worked:

1. **`bin/dotfiles` twice**, then one new tab — proves a re-run is safe, which is
   where this batch's two worst bugs lived.
2. **One fresh tab per terminal** (iTerm2, IntelliJ launched *from an iTerm2
   shell*, Zed) — prompt renders, no error text on open, `❯` correct,
   `git hist -- .nvmrc` colored and exiting without `q`, `type -a bash` listing
   Homebrew first.
3. **One session in a `.envrc`/`.nvmrc` repo** — `cd` in, `nvm current`,
   `which python3`, `echo $POSTGRES_HOST`, round-trip between two repos, back to
   `~`. Separate commands, no `&&`.
4. **Sourcetree** — the GUI case. Push to a *local* remote so nothing is
   published:
   ```bash
   git init --bare ~/.cache/dotfiles/hooktest/<repo>.git
   git -C ~/Developer/<repo> remote add hooktest ~/.cache/dotfiles/hooktest/<repo>.git
   # push main to `hooktest` in Sourcetree; watch for real `node:`/`pnpm:` versions
   git -C ~/Developer/<repo> remote remove hooktest && trash ~/.cache/dotfiles/hooktest
   git -C ~/Developer/<repo> config --get branch.main.remote   # must still be origin
   ```
   The pre-push hook has no remote-specific logic, so a `file://` remote
   exercises it identically. An existing branch is enough — no commit needed.

Run the filesystem-only halves yourself instead of asking (`Include` count in
`~/.ssh/config`, `ssh -G`, `ls -l ~/.zshenv`, which fragments `~/.bashrc`
sources).

## When a criterion fails

Investigate before changing anything, and consider that **the criterion may be
what is wrong**. Both have happened here:

- A criterion claimed `direnv` "appends" while its comment said "prepends" —
  `direnv hook bash` settled it in one command. The comment was stale; the code
  was right.
- A criterion said `_guard_profiles` "aborts" for both halves; it aborts for one
  and warns for the other. The criterion was wrong.

Check the actual code and the actual tool output. Do not trust a summary, a
comment, or a previous session's conclusion — three of this batch's dead ends
were confidently-documented wrong theories.

## Load-bearing things that look like bugs

Read the comment above the code before "fixing" one.

- **The nvm hook appends to `PROMPT_COMMAND`, never prepends.** It must run after
  direnv, which restores its entry-time PATH snapshot on leaving a project.
- **The nvm hook runs every prompt, not on `cd`.** A `git checkout` that rewrites
  `.nvmrc` in place moves neither `$PWD` nor the path. The cached path is
  builtins only, so it costs no forks.
- **`shellenv.sh` skips `brew shellenv` only when `HOMEBREW_PREFIX` and PATH
  agree *and* Homebrew precedes `/usr/bin` and `/bin`.** Each weaker guard broke
  something real, the last being macOS `path_helper` demoting Homebrew below the
  system dirs in every login shell — after which `/bin/bash` 3.2 wins and every
  `#!/usr/bin/env bash` tool silently downgrades.
- **`comply365/*` fragments resolve nvm at runtime, not load time.** `comply365`
  is sourced before `software/node`, so a source-time `command -v nvm` guard
  skips registration entirely.
- **`PS1` is set once, plainly.** Do not reintroduce a per-prompt rebuild or a
  per-terminal branch. A garbled `❯` in IntelliJ was chased for a session with
  both; the cause was `software/iterm2/`'s integration being loaded there by a
  guard that excluded only Zed.
- **`$LESS` must contain no startup-computed option value.** `less` rejects the
  *entire* variable when one option is malformed, losing `--RAW-CONTROL-CHARS`
  and `--quit-if-one-screen` together — uncolored output that waits for `q`.

## Writing scripts and checks in this repo

- Interactive shells alias standard commands (`env` is `env | sort`), and a hook
  inherits the user's profile. Use `"$BASH"` and `/usr/bin/env`, never bare
  `bash`/`env`, and prefix wrapped builtins with `command`.
- `warn` is overridden in `src/common.rb` to `puts` — it goes to **stdout**.
- Anything the bootstrap runs must parse under stock `/usr/bin/ruby` (2.6);
  rbenv does not exist yet at that point.
- `git ls-files` sorts cached and untracked separately, so committing a file
  reorders the list. Sort explicitly wherever content is hashed.
- `script` cannot allocate a pty in the agent sandbox, and tool shells have no
  tty — anything about rendering or interactive paging needs the user's eyes.

## File map

| Path | Role |
|---|---|
| `software/comply365/SPEC.md` | The criteria, plus the `manual-checks` block |
| `software/comply365/{cortex,web-safety}.{rb,bashrc}` | direnv hook; auto-`nvm use` |
| `software/comply365/{zsh.rb,zshenv}` | Homebrew + nvm for every zsh |
| `.claude/hooks/comply365-spec-check.sh` | Stop-hook verifier (`[auto]`) |
| `.claude/hooks/comply365-signoff.sh` | Records a human verdict + code digest |
| `.claude/hooks/lib/` | Probes the verifier calls |
| `.claude/tools/zsh-drift.sh` | What a repo's setup.sh left behind |
| `.claude/settings.json` | Wires both Stop hooks |
| `CLAUDE.md` | The same contract, for sessions that never invoke this skill |
