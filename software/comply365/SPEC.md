# Shell integration — acceptance criteria

Scope: `software/direnv/`, `software/comply365/jira.*` and the shared pieces they
depend on (`software/bash/prompt-command.bash`, `software/node/nvm-loader.sh`,
`software/homebrew/shellenv.sh`).

`bin/dotfiles` regenerates `~/.bashrc` from scratch on every run, so the only
durable place for shell config is a fragment in this repo. The work repos now
run in Bash and zsh on their own, so nothing here re-expresses their setups; the
one tool they share, direnv, is an ordinary `software/direnv` entry. The
interactive shell is always Bash.

Criteria ids are stable; a gap in the numbering is a removed criterion.
`[auto]` criteria were checked by a script that no longer exists; they are
plain statements to verify when the files change. `[eyes]` criteria can only be
confirmed in a real terminal or GUI app.


## direnv / venv (`direnv.rb`, `bashrc.bash`)

- **AC-15 [auto]** The hook is re-added on every `bin/dotfiles` run with no
  hand-rolled duplicate guard: `direnv hook bash` emits its own `_direnv_hook`
  check before it prepends itself to `PROMPT_COMMAND`.
- **AC-17 [eyes]** `cd` into cortex activates the uv `.venv` (`.venv/bin` on
  PATH, `python3` inside it) and loads `.env`; `cd` out deactivates. One-time
  `direnv allow` per clone is expected.
- **AC-18 [eyes]** The prompt shows `[venv: cortex]` — rendered by us from
  `$VIRTUAL_ENV`, since direnv sets that variable and deliberately never touches
  `PS1`. No doubled `(cortex)`, no stray quotes, no per-prompt fork.


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
`bash/prompt.bash` draws the prompt), and they are what actually gets noticed
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
  does. Two independent halves, in two different files: `software/watch/bashrc.bash`
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
  the managed fragment is linked
  under `~/.ssh/config.d/`, and the config is never left group- or
  world-writable (ssh refuses it). Created fresh, it is mode `600` even under a
  permissive umask.
- **AC-32 [auto]** The live generated `~/.bashrc` sources each of this batch's
  fragments exactly once, with `prompt-command.bash` ahead of
  `history.bash` and `prompt.bash` — the helpers those two register through.
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


## Work utilities (`jira.rb`, `jira.bash`)

Not a work repo's setup re-expressed: a command for the `work` profile only,
kept here because it is work-specific.

- **AC-39 [auto]** `jira <number>` opens `<prefix><number>` through `browse`
  (`software/bash/commands.bash`), where `<prefix>` is the first line of
  `~/.config/dotfiles/jira`, e.g. `https://<site>.atlassian.net/browse/<PROJECT>-`.
  The site and project key live only in that per-machine file, never in this
  public repo (AC-4). Anything but exactly one all-digit argument is a usage
  error, and a missing or empty file is an error naming the file; neither opens
  anything. `jira.rb` warns during the `bin/dotfiles` run while the file is
  missing or empty, since nothing here can create it.


## Manual criteria

The `[eyes]` criteria above cannot be verified from a script — they need a real
terminal, a real `cd`, or a GUI app. Each entry below lists the steps.

Format: `<AC-id>|<comma-separated files the check depends on>|<what to do>`

<!-- manual-checks
AC-17|software/direnv/direnv.rb,software/direnv/bashrc.bash|In a fresh terminal: `cd ~/Developer/cortex`, then `which python3` (expect a path inside the repo's .venv) and `echo $POSTGRES_HOST` (expect a value from .env, not empty). `cd ..` and confirm both revert.
AC-18|software/bash/prompt.bash,software/direnv/bashrc.bash|In the same cortex shell, confirm the prompt shows `[venv: cortex]` exactly once — no doubled `(cortex)`, no stray quote characters — and that typing feels instant (no per-keystroke lag).
AC-25|software/homebrew/shellenv.sh|In EACH of iTerm2, IntelliJ's terminal and Zed's terminal: run `git hist -- .nvmrc` inside ~/Developer/cortex. It must print history with no "Oh my! That's a very old version of bash" line. Also run `type -a bash` and confirm the Homebrew path is listed first.
AC-26|software/bash/prompt.bash,software/direnv/bashrc.bash|Open a fresh tab in EACH of iTerm2, IntelliJ's terminal and Zed's terminal: no error text on open, the prompt renders with its path/git/venv segments, and blank-line spacing appears from the second prompt on.
AC-27|software/bash/prompt.bash,software/iterm2/bashrc.bash|In all three terminals, confirm the prompt's `❯` renders correctly (not `â ¯`). Include the case that used to fail: run `idea .` from an iTerm2 shell and check IntelliJ's terminal there. Then, in each terminal, `echo "$PROMPT_COMMAND" | command grep -c __iterm2_prompt_command` must print 0 in IntelliJ and Zed and 1 in iTerm2 (where the integration is wanted). Do NOT judge this from `printf '%q' "$PS1"`: the integration's own preexec restores the unwrapped PS1 before every command, so a working iTerm2 never shows `133` markers there and their absence elsewhere proves nothing.
AC-28|software/watch/bashrc.bash,software/git/bin/git-hist|Run `git hist` and then `watch git hist` in the same repo, side by side: the colors must match. Report fail if watch shows plain/uncolored output.
AC-33|software/direnv/direnv.rb,software/ssh/ssh.rb|ONE terminal is enough — the per-terminal sweep is AC-25/26/27, and the cd behaviors are AC-17/18. Run `bin/dotfiles` twice in a row: both must finish with "Okey dokey" and no error output. Then, in that same tab: (a) `command grep -cxF 'Include ~/.ssh/config.d/*' ~/.ssh/config` prints 1 — other tools' own `Include` lines (Colima adds one for its VM) are expected and not counted; (b) `ssh -G gitlab.com | command grep -i identityfile` resolves; (c) `ls -l ~/.zshenv` is still a symlink into the repo. Finally open ONE new tab and run `echo "$PROMPT_COMMAND" | tr ';' '\n' | command grep -n .` — among OUR hooks, `__comply365_auto_nvm_use` must be the LAST one and `_direnv_hook` must appear somewhere before it, with `__prompt_blank_lines`, `__history_sync` and `__venv_ps1_update` all present, no name appearing twice, and no error output. Only "direnv before nvm, nvm last" is being asserted — that is what this repo controls. Where direnv itself lands among the middle four depends on direnv's own generated snippet (it currently prepends, which is why it appears first despite comply365 being sourced last); a future direnv that appended instead would still satisfy the invariant. A terminal with shell integration wraps that list with its own entries (iTerm2 adds `__bp_precmd_invoke_cmd` / `__iterm2_prompt_command` / `__bp_interactive_mode`, IntelliJ adds `__jetbrains_intellij_command_precmd`) — expected, not a failure; only the relative order of our own hooks is being asserted.
AC-35|software/bash/pager.bash,software/diff/bin/diff-pager,software/git/bin/git-hist|In EACH of iTerm2, IntelliJ and Zed: `cd ~/Developer/cortex && git hist -- .nvmrc`. The SHA/author/date must be visibly dimmer than the commit message, and the command must return to the prompt on its own without needing `q`.
-->
