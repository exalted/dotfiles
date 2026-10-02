# comply365 shell integration — acceptance criteria

Scope: `software/comply365/` and the shared pieces it depends on
(`software/bash/prompt-command.bashrc`, `software/node/nvm-loader.sh`,
`software/homebrew/shellenv.sh`).

Premise the whole directory exists for: `bin/dotfiles` regenerates `~/.bashrc`
from scratch on every run, so anything a work repo's `setup.sh` appends there is
erased. These files re-express those needs as dotfiles-owned fragments. The
interactive shell is always Bash; zsh is never used by hand, but must keep
working because some work repos ship zsh git hooks.

`[auto]` criteria are checked by `.claude/hooks/comply365-spec-check.sh`.
`[eyes]` criteria can only be confirmed in a real terminal or GUI app.

## Structure

- **AC-1 [auto]** `cortex.rb`, `web-safety.rb`, `zsh.rb`, `jira.rb` are executable
  and each registered in `profiles.rb` under `work` as `comply365/<name>`. The
  sourced fragments (`cortex.bashrc`, `web-safety.bashrc`, `jira.bashrc`,
  `zshenv`) are **not** executable — `_defined_software_names` only counts executable files, and a
  fragment that looks like a software entry breaks `_guard_profiles`.
- **AC-2 [auto]** Every file parses: `bash -n` on the `.bashrc` fragments,
  `zsh -n` on `zshenv`, and `ruby -c` under **stock `/usr/bin/ruby` (2.6)** on
  every `.rb` file — `bin/dotfiles` bootstraps before rbenv exists.
- **AC-3 [auto]** These files install nothing. The work repos' own setups own
  installing direnv (cortex's Brewfile) and node/nvm (`software/node`); dotfiles
  only wires configuration. No `brew` calls in the `.rb` files.
- **AC-4 [auto]** dotfiles is a public repo. Bare repo names — `comply365`,
  `cortex`, `web-safety`, `web-cockpit`, and any repo added to the tracked repos
  table — may appear; GitLab repo paths, the org name and an Atlassian site hostname
  may not. The check is a
  denylist on the latter, so the name list above is a convention the *writer*
  keeps, not something the script enforces: prose about what an internal setup
  script does is not caught mechanically. Keep verdicts in that table generic.

## nvm auto-use on cd (`web-safety.bashrc`)

- **AC-5 [auto]** The hook registers even when `nvm` does not exist at load
  time. `comply365/*` is sourced *before* `software/node`, so a source-time
  `command -v nvm` guard silently skips registration entirely. nvm is resolved —
  and loaded via the shared loader if needed — at runtime, inside the hook.
- **AC-6 [auto]** Registered with `__prompt_command_append`, never prepend: it
  must run **after** direnv, which restores its entry-time PATH snapshot when you
  leave a project and would otherwise undo the `nvm use`.
- **AC-7 [auto]** Registration is idempotent, the composed `PROMPT_COMMAND`
  parses under `bash -n`, and it is not exported.
- **AC-8 [auto]** Runs on every prompt, not gated on `$PWD` changing — a
  `git checkout` that rewrites `.nvmrc` in place moves neither `$PWD` nor the
  file path.
- **AC-9 [auto]** The short-circuit key is `.nvmrc path | pinned version | PATH`.
  All three matter: the version catches an in-place rewrite, PATH catches
  direnv's restore. The cached case must cost zero forks (builtins only).
- **AC-10 [auto]** A version with no installed match warns **once per version**
  and never runs an unattended `nvm install`; no state is cached in that branch,
  so installing it from another terminal is picked up.
- **AC-11 [auto]** A directory with no `.nvmrc` anywhere up the tree reverts to
  `nvm version default` (which dotfiles pins to `system`). This goes beyond
  web-safety's own zsh hook, which never reverts.
- **AC-12 [auto]** The `.nvmrc` walk is ours, not nvm's private
  `nvm_find_nvmrc`: it checks `/.nvmrc` like nvm does, reads the first line only,
  and strips trailing whitespace so a CRLF file doesn't resolve to `N/A`.
- **AC-13 [auto]** State is recorded only after the Node on PATH is the one the
  directory asked for, so a failed switch retries next prompt instead of being
  cached as success.
- **AC-14 [eyes]** Round-trip works every time: cortex → web-safety → cortex →
  web-cockpit → cortex tracks each `.nvmrc`; leaving them all lands on `system`.
  The route returns to cortex between the other two because only cortex pins a
  different major (22, vs 24 in both others), so only a hop through it actually
  demonstrates a switch. web-cockpit is included because it is the repo that
  proves the walk is generic — it got zero per-project wiring, so if it tracks
  its own `.nvmrc` then the mechanism, not a per-project file, is what works.

## direnv / venv (`cortex.rb`, `cortex.bashrc`)

- **AC-15 [auto]** The hook is re-added on every `bin/dotfiles` run, guarded on
  `command -v direnv`, with no hand-rolled duplicate guard — `direnv hook bash`
  emits its own `_direnv_hook` check, and it prepends, which is what leaves the
  nvm hook last.
- **AC-16 [auto]** A missing direnv **warns** during the dotfiles run rather than
  silently no-oping, because the failure mode otherwise is invisible: no venv,
  no `.env`.
- **AC-17 [eyes]** `cd` into cortex activates the uv `.venv` (`.venv/bin` on
  PATH, `python3` inside it) and loads `.env`; `cd` out deactivates. One-time
  `direnv allow` per clone is expected.
- **AC-18 [eyes]** The prompt shows `[venv: cortex]` — rendered by us from
  `$VIRTUAL_ENV`, since direnv sets that variable and deliberately never touches
  `PS1`. No doubled `(cortex)`, no stray quotes, no per-prompt fork.

## zsh reachability (`zsh.rb`, `zshenv`)

- **AC-19 [auto]** `~/.zshenv` is a symlink to the managed file, installed with
  `backup: true`. `~/.zshrc` and `~/.zprofile` stay untouched — the work repos'
  setups append to those with their own markers.
- **AC-20 [auto]** `zshenv` resolves its own location through the symlink
  (`${${(%):-%x}:A:h}`) so the clone can live anywhere; it sources the *shared*
  `homebrew/shellenv.sh` and the *shared* `node/nvm-loader.sh` rather than
  carrying copies, and it uses Homebrew's nvm — not a second curl-installed one.
- **AC-21 [auto]** nvm is lazy: a stub that `unfunction`s itself on first call.
  Sourcing `nvm.sh` eagerly costs ~200ms in *every* zsh, including the one-shot
  ones a pre-commit runner spawns per file.
- **AC-22 [auto]** A bare zsh with a launchd-like PATH (`/usr/bin:/bin:/usr/sbin:/sbin`)
  finds `brew`, `node`, `pnpm`, `nvm` and `direnv` after reading `~/.zshenv`, and
  `zsh -c true` stays under ~0.1s.
- **AC-23 [eyes]** Committing/pushing web-safety from Sourcetree runs its zsh
  hooks with no "command not found". From a terminal it worked only by accident,
  inheriting Bash's PATH.

## Notes that keep tripping reviews

- `PS1` is set **once**, at source time, identically in every terminal — and
  that is now sufficient, because the garbled `❯` in IntelliJ was never
  IntelliJ's fault. It was iTerm2's shell integration, loaded there by a guard
  that excluded only Zed (see AC-36), exporting an OSC-133-wrapped `PS1` that
  came back byte-corrupted. Two earlier theories were wrong and should not be
  revived: a per-prompt `PS1` rebuild handing IntelliJ a single-line prompt
  (costs a prompt hook, reverts `conda activate` and any ad-hoc `PS1=` one
  prompt later), and an "asynchronous `TERMINAL_EMULATOR`" race — the variable
  is in fact present in IntelliJ's shell from the start.
- Whether a change needs a `bin/dotfiles` re-run: a brand-new sourced file does
  (its `source` line is only written during a run); a content change to an
  already-sourced or symlinked file does not.

## Bash resolution and terminal rendering

Not comply365-specific, but they break *because* of files in this batch's
dependency set (`homebrew/shellenv.sh` decides which `bash` wins;
`bash/prompt.bashrc` draws the prompt), and they are what actually gets noticed
when something here regresses.

- **AC-24 [auto]** Homebrew's `bash` resolves before macOS's `/bin/bash` (3.2) in
  both a terminal-like and a GUI-like environment — including the exact case that
  broke it before: `HOMEBREW_PREFIX` already exported while PATH does *not*
  contain its bin dir. When it regresses, anything with a `#!/usr/bin/env bash`
  shebang silently falls back to bash 3.2.
- **AC-25 [eyes]** `git hist` (any repo, any of the three terminals) must not
  print *"Oh my! That's a very old version of bash"* — `emojify` reaches it
  through `core.pager`, so this is the user-visible symptom of AC-24.
- **AC-26 [eyes]** Everything works in all three terminals: iTerm2, IntelliJ's
  terminal, and Zed's terminal.
- **AC-27 [eyes]** The `❯` in `PS1` (and anywhere else it appears) renders as
  `❯` — not `â ¯` or a box — in **all three** terminals, including IntelliJ's,
  and including an IntelliJ launched with `idea .` from an iTerm2 shell. That
  last case is the one that used to fail: IntelliJ inherits no `ZED_TERM` there,
  so before AC-36 it loaded iTerm2's integration and got a mojibaked `PS1`.
- **AC-28 [eyes]** `watch git hist` renders colors the same way plain `git hist`
  does. Two independent halves, in two different files: `software/watch/bashrc`
  aliases `watch --color` so it forwards ANSI through, and
  `software/git/bin/git-hist` passes `git log --color` so git emits ANSI even to
  a non-tty. Break either and the output goes plain.

## Running `bin/dotfiles` must not break anything

It regenerates `~/.bashrc` and re-runs every entry script on every invocation,
so "works once" is not the bar — it has to be safe to run repeatedly, on a
machine that is already set up.

- **AC-29 [auto]** `_guard_profiles` passes, in both of its halves, which do
  **not** behave the same: a name in `profiles.rb` with no runnable definition
  **aborts** the run before anything is configured, while a `software/` entry
  configured in no profile only **warns** and the run proceeds. So the abort
  half is self-enforcing and the warn half is not — it needs asserting here, or
  a stale entry accumulates unnoticed.
- **AC-30 [auto]** Running this batch's entry scripts **twice** against a
  throwaway `$HOME` is idempotent: one `source` line per fragment, one
  `Include` in `~/.ssh/config`, one backup — not one per run.
- **AC-31 [auto]** The same double run is non-destructive: a `~/.ssh/config`
  kept outside this repo keeps its `Host` entries beneath the `Include`, a
  pre-existing `~/.zshenv` survives in `.backup`, the managed fragment is linked
  under `~/.ssh/config.d/`, and the config is never left group- or
  world-writable (ssh refuses it). Created fresh, it is mode `600` even under a
  permissive umask.
- **AC-32 [auto]** The live generated `~/.bashrc` sources each of this batch's
  fragments exactly once, with `prompt-command.bashrc` ahead of
  `history.bashrc` and `prompt.bashrc` — the helpers those two register through.
- **AC-33 [eyes]** The real thing: `bin/dotfiles` completes twice in a row with
  no errors, and the shell still works afterwards. Cannot be automated — it
  needs sudo, Homebrew, and `chsh`.

- **AC-34 [auto]** `$LESS` is well-formed and `less` accepts it whole. It must
  carry `--RAW-CONTROL-CHARS` and `--quit-if-one-screen`, and no option value in
  it may be computed at shell startup: `less` rejects the *entire* variable when
  one option is malformed, so a failed `tput` silently costs colors AND
  quit-on-one-screen at once — which is how a terminal that sizes its panel
  asynchronously ends up behaving differently from the others.
- **AC-35 [eyes]** In all three terminals, `git hist -- <file>` on a one-screen
  result prints in color and exits without a keypress.

- **AC-36 [auto]** iTerm2's shell integration loads in iTerm2 and **not** in
  Zed's or IntelliJ's terminal. It self-guards only on `$TERM` and
  interactivity, never on whether it is really inside iTerm2, and in IntelliJ it
  `export`s an OSC-133-wrapped `PS1` that comes back byte-corrupted (`❯` read as
  Latin-1 and re-encoded). Excluded by `$ZED_TERM` and
  `$TERMINAL_EMULATOR=JetBrains-JediTerm` — there is no usable positive signal,
  since every variable iTerm2 exports is inherited by whatever is launched from
  it, and IntelliJ sets `TERM_PROGRAM=iTerm.app` itself.

## Staying current with the work repos' own setups

- **AC-37 [auto]** Every repo in the tracked repos table
  (`.claude/skills/comply365/SKILL.md`) has a recorded baseline commit, and its
  `setup/`, `local/`, `.envrc`, git hooks, runtime pins and local-dev docs are unchanged
  since it — `.claude/tools/setup-review.sh` exits 0. Our fragments only
  re-express a setup we have actually read, so an unread change means the wiring
  is trusted on faith.

  The script deliberately stops at *finding* the delta: a diff cannot tell an
  rc-file write from a reworded paragraph, so the verdict is a reading, recorded
  back into that table. A repo that is not cloned is reported and skipped —
  neither a pass nor a failure, since nothing can be read.

  `package.json` is compared by `engines`, `packageManager`, `volta`, `scripts`
  and `type` alone, and `pyproject.toml` by its `requires-python` line alone.
  Diffing either whole file would fire on every dependency bump, and a gate that
  always fires is a gate nobody reads.

  Note what is deliberately **not** in the sign-off digest: `SKILL.md`. Recording
  a routine "nothing relevant changed" verdict must not expire ten `[eyes]`
  sign-offs. It does not need to — a delta that genuinely affects us is wired by
  editing the `.bashrc`/`.rb` files, and *those* are in the digest, so the
  expiry happens through the real change rather than through the bookkeeping.

- **AC-38 [auto]** No tracked repo ships `.githooks/` while its
  `core.hooksPath` is unset. Git then silently falls back to `.git/hooks`, which
  holds nothing but `.sample` files, so **every hook in the repo is dead** — and
  it fails open, with no error to notice. Each of these repos sets
  `core.hooksPath` from its own `setup.sh`, so an unset value means that setup
  has never run in the clone.

  This is the one hole all the zsh work could not have covered: AC-19..23 make a
  zsh hook *runnable* from a GUI app, which is worth nothing if git never invokes
  it. `web-cockpit` sat in exactly that state and nothing noticed, because a
  repo with no wiring of its own has no fragment, no profile entry and no
  criterion pointing at it.

  Checked per repo by `.claude/tools/setup-review.sh`, alongside AC-37.

## Work utilities (`jira.rb`, `jira.bashrc`)

Not a work repo's setup re-expressed: a command for the `work` profile only,
kept here because it is work-specific.

- **AC-39 [auto]** `jira <number>` opens `<prefix><number>` through `browse`
  (`software/bash/commands.bashrc`), where `<prefix>` is the first line of
  `~/.config/dotfiles/jira`, e.g. `https://<site>.atlassian.net/browse/<PROJECT>-`.
  The site and project key live only in that per-machine file, never in this
  public repo (AC-4). Anything but exactly one all-digit argument is a usage
  error, and a missing or empty file is an error naming the file; neither opens
  anything. `jira.rb` warns during the `bin/dotfiles` run while the file is
  missing or empty, since nothing here can create it.

## Manual criteria

The `[eyes]` criteria above cannot be verified from a script — they need a real
terminal, a real `cd`, or a GUI app. The Stop hook reads the block below,
prints the steps, and treats each one as *unconfirmed* until you say it passed.
A sign-off is invalidated when the files it depends on change again.

Format: `<AC-id>|<comma-separated files the sign-off depends on>|<what to do>`

<!-- manual-checks
AC-14|software/comply365/web-safety.bashrc|IMPORTANT: run each `cd` and each `nvm current` as SEPARATE commands. The hook runs from PROMPT_COMMAND, i.e. after your command line finishes, so a chained `cd X && nvm current` reports the version from BEFORE the hook ran for X — every reading comes out one step behind and it looks broken when it is not. In a fresh terminal, `cd` into each of the following IN THIS ORDER, running `nvm current` after each one: cortex (expect v22.12.0), web-safety (v24.13.1), cortex again (v22.12.0), web-cockpit (v24.13.1), cortex again (v22.12.0). The route deliberately returns to cortex between the other two: web-safety and web-cockpit both pin 24.13.1, so hopping straight between them reports 24.13.1 whether the hook ran or not — that reading proves nothing. Only a transition to or from cortex's 22.12.0 actually demonstrates a switch. web-cockpit is the repo that matters most: it has no software/comply365 file of its own, so it is what proves the .nvmrc walk is generic rather than per-project — expect no "N/A"/"system" and no nvm install prompt there. Finally `cd ~` and expect `system`.
AC-17|software/comply365/cortex.rb,software/comply365/cortex.bashrc|In a fresh terminal: `cd ~/Developer/cortex`, then `which python3` (expect a path inside the repo's .venv) and `echo $POSTGRES_HOST` (expect a value from .env, not empty). `cd ..` and confirm both revert.
AC-18|software/bash/prompt.bashrc,software/comply365/cortex.bashrc|In the same cortex shell, confirm the prompt shows `[venv: cortex]` exactly once — no doubled `(cortex)`, no stray quote characters — and that typing feels instant (no per-keystroke lag).
AC-23|software/comply365/zshenv,software/comply365/zsh.rb|Do NOT push to origin — nothing needs publishing. The pre-push hook has no remote-specific logic, so a local remote exercises it identically: `git init --bare ~/.cache/dotfiles/hooktest/web-safety.git` then `git -C ~/Developer/web-safety remote add hooktest ~/.cache/dotfiles/hooktest/web-safety.git`. In Sourcetree (NOT a terminal) push main to `hooktest`. The hook must print real versions — `node: vX, pnpm: Y` — rather than "command not found"; that line alone satisfies the criterion, so cancel once you see it instead of waiting for pnpm test/build. An existing branch is enough, no commit required. Afterwards: `git remote remove hooktest`, trash the bare repo, and confirm `git config --get branch.main.remote` is still `origin`.
AC-25|software/homebrew/shellenv.sh|In EACH of iTerm2, IntelliJ's terminal and Zed's terminal: run `git hist -- .nvmrc` inside ~/Developer/cortex. It must print history with no "Oh my! That's a very old version of bash" line. Also run `type -a bash` and confirm the Homebrew path is listed first.
AC-26|software/bash/prompt.bashrc,software/comply365/cortex.bashrc,software/comply365/web-safety.bashrc|Open a fresh tab in EACH of iTerm2, IntelliJ's terminal and Zed's terminal: no error text on open, the prompt renders with its path/git/venv segments, and blank-line spacing appears from the second prompt on.
AC-27|software/bash/prompt.bashrc,software/iterm2/bashrc|In all three terminals, confirm the prompt's `❯` renders correctly (not `â ¯`). Include the case that used to fail: run `idea .` from an iTerm2 shell and check IntelliJ's terminal there. Then, in each terminal, `echo "$PROMPT_COMMAND" | command grep -c __iterm2_prompt_command` must print 0 in IntelliJ and Zed and 1 in iTerm2 (where the integration is wanted). Do NOT judge this from `printf '%q' "$PS1"`: the integration's own preexec restores the unwrapped PS1 before every command, so a working iTerm2 never shows `133` markers there and their absence elsewhere proves nothing.
AC-28|software/watch/bashrc,software/git/bin/git-hist|Run `git hist` and then `watch git hist` in the same repo, side by side: the colors must match. Report fail if watch shows plain/uncolored output.
AC-33|software/comply365/cortex.rb,software/comply365/web-safety.rb,software/comply365/zsh.rb,software/ssh/ssh.rb|ONE terminal is enough — the per-terminal sweep is AC-25/26/27, and the cd behaviors are AC-14/17/18. Run `bin/dotfiles` twice in a row: both must finish with "Okey dokey" and no error output. Then, in that same tab: (a) `command grep -cxF 'Include ~/.ssh/config.d/*' ~/.ssh/config` prints 1 — other tools' own `Include` lines (Colima adds one for its VM) are expected and not counted; (b) `ssh -G gitlab.com | command grep -i identityfile` resolves; (c) `ls -l ~/.zshenv` is still a symlink into the repo. Finally open ONE new tab and run `echo "$PROMPT_COMMAND" | tr ';' '\n' | command grep -n .` — among OUR hooks, `__comply365_auto_nvm_use` must be the LAST one and `_direnv_hook` must appear somewhere before it, with `__prompt_blank_lines`, `__history_sync` and `__venv_ps1_update` all present, no name appearing twice, and no error output. Only "direnv before nvm, nvm last" is being asserted — that is what this repo controls. Where direnv itself lands among the middle four depends on direnv's own generated snippet (it currently prepends, which is why it appears first despite comply365 being sourced last); a future direnv that appended instead would still satisfy the invariant. A terminal with shell integration wraps that list with its own entries (iTerm2 adds `__bp_precmd_invoke_cmd` / `__iterm2_prompt_command` / `__bp_interactive_mode`, IntelliJ adds `__jetbrains_intellij_command_precmd`) — expected, not a failure; only the relative order of our own hooks is being asserted.
AC-35|software/bash/pager.bashrc,software/diff/bin/diff-pager,software/git/bin/git-hist|In EACH of iTerm2, IntelliJ and Zed: `cd ~/Developer/cortex && git hist -- .nvmrc`. The SHA/author/date must be visibly dimmer than the commit message, and the command must return to the prompt on its own without needing `q`.
-->
