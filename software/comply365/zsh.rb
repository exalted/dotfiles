#!/usr/bin/env ruby
require_relative '../../src/helpers'

# We use Bash, so dotfiles doesn't manage zsh — with this one exception.
#
# Symlink our managed ~/.zshenv into place. Its whole job is to guarantee that
# any zsh spawned behind our back — notably the zsh git hooks some work repos
# ship (web-safety), when triggered from GUI apps like Sourcetree — can still
# find Homebrew-installed tools such as pnpm/node. See the zshenv file itself
# for the full explanation.
#
# Nothing is installed here: Homebrew comes from the bootstrap step and nvm from
# software/node. We only link the file. `backup: true` preserves any pre-existing
# ~/.zshenv (once) instead of clobbering it.
link_to_home_relative 'zshenv', '.zshenv', backup: true
