#!/usr/bin/env ruby
require_relative '../../src/helpers'

# cortex uses direnv: its .envrc runs `layout python3` + `dotenv .env`, so
# cd-ing into the repo auto-activates the uv-managed .venv and loads .env.
# cortex's own setup already installs direnv (via its Brewfile) and appends
# `eval "$(direnv hook bash)"` to ~/.bashrc — but `bin/dotfiles` regenerates
# ~/.bashrc from scratch on every run and wipes that hook. So we don't install
# direnv here (cortex's setup owns that); we only re-add the hook so it survives
# every regeneration. The fragment no-ops if direnv is absent — which would
# otherwise leave the .venv/.env auto-activation silently broken, so warn here
# instead, where there's a person watching the run.
warn "direnv isn't installed, so cortex's .venv/.env won't auto-activate on cd. " \
     "Run cortex's own setup (its Brewfile installs direnv), then re-run dotfiles." unless cmd_exists?('direnv')

bash_source_relative 'cortex'
