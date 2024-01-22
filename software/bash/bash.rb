#!/usr/bin/env ruby
require_relative '../../src/helpers'

brew 'bash-completion'
bash_source "/opt/homebrew/etc/profile.d/bash_completion.sh"

link_to_home_relative 'inputrc', '.inputrc'
link_to_home_relative 'hushlogin', '.hushlogin'

bash_source_relative 'locale'
bash_source_relative 'paths'
bash_source_relative 'prompt'
bash_source_relative 'various'
bash_source_relative 'history'
bash_source_relative 'commands'
bash_source_relative 'aliases'
bash_source_relative 'pager'
bash_source_relative 'colors'
bash_source_relative 'man'
