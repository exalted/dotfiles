#!/usr/bin/env ruby
require_relative '../../src/helpers'

# web-safety pins Node via .nvmrc and
# expects a `chpwd` hook to auto-run `nvm use` on cd. Its setup only installs
# that hook into ~/.zshrc using zsh-only builtins, so it never fires in Bash.
#
# nvm itself is already installed and loaded by software/node (which matches
# `brew info nvm`'s caveat), so we deliberately do NOT install or re-load nvm
# here — we only add the Bash equivalent of the auto-use-on-cd hook.
bash_source_relative 'web-safety'
