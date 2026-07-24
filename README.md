dotfiles
========

This assumes your shell of choice is Bash.

## "Install"

Clone this repository and run the entry point:

```bash
git clone https://github.com/exalted/dotfiles.git ~/Development/dotfiles
cd ~/Development/dotfiles/
bin/dotfiles
```

The first run aborts until you've selected a profile — see **Profiles** below.

## Usage

Whenever you feel like, run `bin/dotfiles` to keep your environment up to
date.

## Bootstrap

Some software is foundational — `bin/dotfiles` can't run without it — so it
isn't profile-configurable. The `bootstrap` step (`src/steps/bootstrap.rb`)
installs it up front, before any profile software: the package manager, the
shell, and Ruby, followed by this repo's own Ruby bundle (`bundle install`).

## Profiles

`profiles.rb` is the registry of profile-configurable software:

* `COMMON` — installed for all profiles.
* `PROFILES['<name>']` — installed only for the current profile.

A profile is selected via `~/.config/dotfiles/profile`:

```bash
mkdir -p ~/.config/dotfiles
echo personal > ~/.config/dotfiles/profile
```

`bin/dotfiles` aborts with these instructions — and the list of valid
profiles — if the file is missing.

## How to add new software

0. Create an executable script at `software/<name>.<ext>` (a flat script)
   or `software/<name>/<name>.<ext>` (its own directory). `<ext>` is one of
   `rb`, `sh`, `py`, `js`; Ruby is encouraged, the rest are welcome.
0. Make it executable (`chmod +x`) and give it a correct shebang
   (`#!/usr/bin/env ruby`, `#!/usr/bin/env bash`, …).
0. Keep it self-contained — it must work when run directly
   (e.g. `software/<name>.rb`), not only through `bin/dotfiles`.
0. List `<name>` in `profiles.rb`, under `COMMON` or a profile. A script
   that isn't listed there is never run.
0. Try to keep scripts as order-independent as possible.

Software that can't follow the naming convention may live anywhere under
`software/` and be listed with a directory-qualified name, `<dir>/<name>`
(for example a script at `some_dir/tool.rb`, listed as `some_dir/tool`).
