#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'bash-completion'
bash_source '/usr/local/etc/bash_completion'

link_to_home_relative 'inputrc', '.inputrc'
link_to_home_relative 'hushlogin', '.hushlogin'

bash_source_relative 'prompt'
bash_source_relative 'various'
bash_source_relative 'history'
bash_source_relative 'commands'
bash_source_relative 'aliases'
bash_source_relative 'pager'
bash_source_relative 'colors'
bash_source_relative 'editors'
bash_source_relative 'man'
