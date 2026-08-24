#!/usr/bin/env ruby
require_relative '../../src/helpers'

# The managed fragment lives under ~/.ssh/config.d/, included from the user's
# own ~/.ssh/config — never symlinked on top of it. Symlinking straight onto
# ~/.ssh/config would replace any pre-existing Host entries outright (jump
# hosts, other keys), and would turn dotfiles' git tree into the target of
# every tool that appends to ~/.ssh/config (gh, JetBrains, 1Password's agent,
# Codespaces).
#
# `config` (this file, or its `work` variant — see profile_specific) is linked,
# not the Include line's target directly, so profiles without SSH config of
# their own still get a harmless fragment instead of ssh.rb aborting.
link_to_home_relative 'config', '.ssh/config.d/dotfiles'
ensure_first_line_at_home '.ssh/config', 'Include ~/.ssh/config.d/*', backup: true, mode: 0o600
