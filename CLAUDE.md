# dotfiles

Personal machine setup. `bin/dotfiles` reads `~/.config/dotfiles/profile` (`work`
or `personal`), runs the `software/<name>` entry scripts listed for that profile
in `profiles.rb`, and **regenerates `~/.bashrc` and `~/.bash_profile` from
scratch on every run**.

That last point drives most of the design: anything appended to `~/.bashrc` from
outside this repo is erased on the next run. The only durable place for shell
config is a `software/<tool>/bashrc.bash` fragment inside this repo.

## This repo is public

It is on GitHub. Before you add or change any file (skills, scripts, `CLAUDE.md`,
settings), check that it holds none of these:

- secrets, tokens, passwords or API keys;
- personal data: names combined with contact details, email addresses, phone
  numbers, user or account IDs;
- organization-internal identifiers: tenant, client or application IDs, internal
  hostnames, URLs, IP addresses, Jira sites or project keys, GitLab repo paths,
  Slack channel links;
- a description of an organization's security setup, such as which permissions
  are or are not granted.

Write instructions generically. Put organization-specific values in untracked
config under `~/.config/dotfiles/`, as `jira` and `pairing-candidates` do.

## Load-bearing things that look like bugs

Each of these was flagged by a review, re-investigated, and kept. Read the
comment above the code before "fixing" one:

- **`prompt.bash` sets `PS1` once, and that is enough.** A garbled `❯` in
  IntelliJ was chased for a whole session with a per-prompt `PS1` rebuild and a
  `TERMINAL_EMULATOR` check; both were wrong. The cause was `software/iterm2/`'s
  shell integration being loaded in IntelliJ's terminal by a guard that excluded
  only Zed — it `export`s an OSC-133-wrapped `PS1` that comes back mojibaked.
  Fixed at the source. Do not reintroduce a per-prompt rebuild: it costs a
  prompt hook and silently reverts `conda activate` or any ad-hoc `PS1=`.
- **`shellenv.sh` skips `brew shellenv` only when `HOMEBREW_PREFIX` *and* PATH
  agree.** Each single-proxy guard broke something real: PATH-only re-prepended
  Homebrew ahead of an nvm-selected Node; `HOMEBREW_PREFIX`-only lost Homebrew
  entirely when a GUI app exported a stale prefix, silently falling back to
  macOS bash 3.2 (the `git hist` / `emojify` failure).

## Writing tests and hooks in this repo

Interactive shells here alias some standard commands (`env` is `env | sort`), and
a hook inherits the user's profile. In scripts, use `"$BASH"` and
`/usr/bin/env` rather than bare `bash`/`env`, and prefix wrapped builtins with
`command`. Anything the bootstrap runs must also parse under stock
`/usr/bin/ruby` (2.6) — rbenv does not exist yet at that point.

## User-scoped Claude Code skills (`software/claude-code/skills/`)

`claude-code.rb` links each skill directory whole into `~/.claude/skills/`:
`common/` on every profile that installs claude-code, `<profile>/` only on that
profile. Never link `~/.claude/skills` itself: Claude Code writes the skills it syncs from claude.ai
into it (`synced/`), and those are not ours to track.

This repo is public, so the rules above apply to skills too: bare repo names and
public company and product names may appear; anything internal may not: GitLab
repo paths, an Atlassian site, colleagues' names and internal IDs (Slack
channels, …). A skill that needs them reads them from an untracked
`~/.config/dotfiles/<skill>/` and ships a placeholder `*.example.*` beside it —
see `pairing-candidates`.
