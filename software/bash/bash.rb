#!/usr/bin/env ruby
require_relative '../../src/helpers'

brew 'bash'
system "sudo chsh -s $(brew --prefix)/bin/bash #{ENV["USER"]}"

brew 'bash-completion@2'
bash_source "#{brew_prefix}/etc/profile.d/bash_completion.sh"

link_to_home_relative 'inputrc', '.inputrc'
link_to_home_relative 'hushlogin', '.hushlogin'

# Out of alphabetical order on purpose: this only defines helpers, and the
# fragments below (plus comply365's) call them to register their prompt hooks.
bash_source_relative 'prompt-command'

# Keep these in alphabetical order:
bash_source_relative 'aliases'
bash_source_relative 'colors'
bash_source_relative 'commands'
bash_source_relative 'editors'
bash_source_relative 'env'
bash_source_relative 'history'
bash_source_relative 'locale'
bash_source_relative 'man'
bash_source_relative 'pager'
bash_source_relative 'paths'
bash_source_relative 'prompt'
bash_source_relative 'various'
