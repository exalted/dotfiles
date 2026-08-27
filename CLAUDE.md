# dotfiles

Personal machine setup. `bin/dotfiles` reads `~/.config/dotfiles/profile` (`work`
or `personal`), runs the `software/<name>` entry scripts listed for that profile
in `profiles.rb`, and **regenerates `~/.bashrc` and `~/.bash_profile` from
scratch on every run**.

That last point drives most of the design: anything appended to `~/.bashrc` from
outside this repo is erased on the next run. The only durable place for shell
config is a `software/<tool>/bashrc` fragment inside this repo.

## Work projects (`software/comply365/`)

Work repos in `~/Developer` expect shell behavior their own `setup.sh` installs
into rc files — into `~/.zshrc` with zsh-only builtins, or into `~/.bashrc`
where this repo then wipes it. `software/comply365/` re-expresses those needs as
dotfiles-owned fragments.

The contract, and it matters: **the projects' own setups install the tools; this
repo only wires configuration.** Never add a `brew` call to a
`software/comply365/*.rb`.

Its three mechanisms are **generic despite their per-project names**:

| File | Covers | Applies to |
|---|---|---|
| `cortex.bashrc` | the `direnv` hook | any repo with an `.envrc` |
| `web-safety.bashrc` | auto-`nvm use` on `cd` | any repo with an `.nvmrc` |
| `zshenv` (via `zsh.rb`) | Homebrew + nvm on PATH for **every** zsh | any repo with zsh git hooks |

### Onboarding a newly cloned work repo

Default answer: **add nothing.** Walk the checklist first.

Step 0, which is not optional even when the answer to everything else is "add
nothing": **add a row to the tracked repos table** in
`.claude/skills/comply365/SKILL.md`, with `-` as the analyzed-at commit. A repo
needing no wiring gets no fragment, no `profiles.rb` entry and no criterion — so
that table is the *only* place it becomes visible. `web-cockpit` was correctly
onboarded with zero wiring and then went a month with dead git hooks precisely
because nothing recorded that it existed.

1. `grep -rE 'bashrc|zshrc|zprofile|nvm|direnv|chpwd' <repo>/setup*/setup.sh` —
   does its setup write to an rc file, or install a runtime manager?
2. Does it have `.envrc`? Covered — `cortex.bashrc` already hooks direnv for
   every directory. The one manual step is `direnv allow` inside the clone.
3. Does it have `.nvmrc`? Covered — the hook walks up from `$PWD`, so it works
   for any repo. `web-cockpit` needed zero changes for exactly this reason.
   Do **not** add a per-project copy of the hook.
4. Are its git hooks `#!/bin/zsh`? Covered by `~/.zshenv`.
5. Only if none of the above covers it: add `software/comply365/<project>.rb`
   (+ a `.bashrc` fragment if it needs one), register it in `profiles.rb` under
   `work`, `chmod +x` the `.rb`, and add acceptance criteria to
   `software/comply365/SPEC.md`.

Known gap, deliberately not solved: hooks with a `#!/bin/sh` or
`#!/usr/bin/env sh` shebang (e.g. `web-cockpit`) get no startup file at all when
a GUI app spawns them — `~/.zshenv` is a zsh mechanism. If one of those fails
from Sourcetree, that is the cause.

## After running a work repo's `setup.sh`

Those scripts mutate shell startup files behind your back: they append to
`~/.zshrc` with zsh-only builtins (inert for us), sometimes to `~/.bashrc`
(which the next `bin/dotfiles` run erases), and they may install a second copy
of a runtime manager. The behavior only becomes durable once it exists as a
fragment in this repo.

So after running any repo's setup — or when a repo is freshly cloned — run:

```
.claude/tools/zsh-drift.sh
```

It reports, per line, what those setups left behind and whether this repo
already provides the same thing for Bash:

- `TRANSIENT` — in `~/.bashrc`, but already durable here. It disappears on the
  next `bin/dotfiles` run and nothing is lost. No action.
- `MIRRORED` — zsh-only, and this repo has the Bash equivalent. No action.
- `UNMIRRORED` — nothing here provides it. **This is the one that needs a
  decision**, and the script's own output lists the four steps: decide whether
  it is shell behavior we need, wire it (preferring the three generic
  mechanisms over a new per-project file), add criteria to `SPEC.md`, then run
  the spec check and get the `[eyes]` criteria re-confirmed.

Exit code is 0 when nothing is unaccounted for, so it is safe to use as a gate.

`zsh-drift.sh` answers "what did that setup leave in my rc files *just now*". It
cannot answer "has that repo's setup *changed* since we wrote our version of
it". That is the other tool:

```
.claude/tools/setup-review.sh
```

Each tracked repo has a row in the tracked repos table in
`.claude/skills/comply365/SKILL.md` recording the commit its `setup/`, git
hooks, runtime pins and local-dev docs were last read at. This diffs each repo's
tip against that commit and stops there — **it never judges the change**, because
a diff cannot tell an rc-file write from a reworded paragraph. Read the diff,
decide whether it touches what we guarantee, then either record the new commit
with a generic one-line verdict (irrelevant) or wire it and add criteria first
(relevant). AC-37 blocks while any delta is unread, so nothing goes unexamined.

It also reports `HOOKS-INACTIVE` (AC-38): a repo that ships `.githooks/` while
`core.hooksPath` is unset has **dead hooks** — git falls back to `.git/hooks`,
which holds only samples, and fails open with no error. That means its own
`setup.sh` never ran in the clone. All the zsh-reachability work is worth
nothing for such a repo, since git never invokes the hook at all.

Onboarding a repo means adding a row with `-` as the commit, so the next run
reports `NEVER-ANALYZED`. A repo not in `~/Developer` is `NO-CLONE`: reported,
never a failure, since nothing can be read.

## Before you finish: do not break what you did not touch

The full playbook for this — onboarding a new work repo, adding criteria,
getting manual ones confirmed, and the traps — is the `comply365` skill
(`.claude/skills/comply365/SKILL.md`, invocable as `/comply365`). Read it
before touching `software/comply365/`; what follows is the short version.

`software/comply365/SPEC.md` is the acceptance criteria for this batch of work.
A `Stop` hook (`.claude/hooks/comply365-spec-check.sh`, wired in
`.claude/settings.json`) verifies the automated ones and refuses to let a
session end quietly while any of them fail.

- Two hooks run on `Stop`, with a deliberate split: the **command** hook owns
  everything executable (it is the only one that can run interpreters — a hook
  agent's Bash tool is restricted to reads), and the **agent** hook owns what
  only reading can catch: a comment that contradicts its code, a criterion with
  no code behind it, behavior with no criterion. If the agent ever reports that
  it could not execute something, that is a prompt bug, not a finding.
- Run it directly at any time:
  `echo '{}' | .claude/hooks/comply365-spec-check.sh`
- It self-gates: it does nothing unless the session touched
  `software/comply365/`, `software/bash/prompt{,-command}.bashrc`,
  `software/node/nvm-loader.sh` or `software/homebrew/shellenv.sh`.
- Criteria marked `[eyes]` cannot be scripted (they need a real terminal, a real
  `cd`, or a GUI app). **Ask the user to run them and wait for a pass/fail** —
  never assume. Record the answer with
  `.claude/hooks/comply365-signoff.sh <AC-id> pass|fail`; a sign-off expires by
  itself when any of the batch's **code** files change. `SPEC.md` itself is
  deliberately not in that digest — correcting a criterion's wording or its
  dependency list should not force a human to re-run everything. The tradeoff:
  if you *tighten* what a criterion asserts, revoke its sign-off by hand
  (`comply365-signoff.sh <AC-id> fail`) so it gets re-confirmed.
- Adding behavior means adding a criterion. A change that cannot be expressed as
  a criterion is a change nobody will be able to verify later.

### Load-bearing things that look like bugs

Each of these was flagged by a review, re-investigated, and kept. Read the
comment above the code before "fixing" one:

- **`prompt.bashrc` sets `PS1` once, and that is enough.** A garbled `❯` in
  IntelliJ was chased for a whole session with a per-prompt `PS1` rebuild and a
  `TERMINAL_EMULATOR` check; both were wrong. The cause was `software/iterm2/`'s
  shell integration being loaded in IntelliJ's terminal by a guard that excluded
  only Zed — it `export`s an OSC-133-wrapped `PS1` that comes back mojibaked.
  Fixed at the source. Do not reintroduce a per-prompt rebuild: it costs a
  prompt hook and silently reverts `conda activate` or any ad-hoc `PS1=`.
- **The nvm hook appends to `PROMPT_COMMAND`, never prepends.** It must run
  *after* direnv, which restores its entry-time PATH snapshot on leaving a
  project and would otherwise undo the `nvm use`.
- **The nvm hook runs every prompt, not on `cd`.** A `git checkout` that
  rewrites `.nvmrc` in place moves neither `$PWD` nor the file path. The cached
  path is builtins only, so it costs no forks.
- **`shellenv.sh` skips `brew shellenv` only when `HOMEBREW_PREFIX` *and* PATH
  agree.** Each single-proxy guard broke something real: PATH-only re-prepended
  Homebrew ahead of an nvm-selected Node; `HOMEBREW_PREFIX`-only lost Homebrew
  entirely when a GUI app exported a stale prefix, silently falling back to
  macOS bash 3.2 (the `git hist` / `emojify` failure).
- **`comply365/*` fragments resolve nvm at runtime, not at load time.**
  `comply365` is sourced before `software/node`, so a source-time
  `command -v nvm` guard skips registration entirely.

### Writing tests and hooks in this repo

Interactive shells here alias some standard commands (`env` is `env | sort`), and
a hook inherits the user's profile. In scripts, use `"$BASH"` and
`/usr/bin/env` rather than bare `bash`/`env`, and prefix wrapped builtins with
`command`. Anything the bootstrap runs must also parse under stock
`/usr/bin/ruby` (2.6) — rbenv does not exist yet at that point.
