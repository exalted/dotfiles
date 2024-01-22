#!/usr/bin/env ruby
require_relative '../../src/helpers'

# Default version is set in `software/python/bashrc` via `PATH`
brew 'python@3.11'
brew 'python@3.10'
brew 'python@3.9'
# Older versions:
brew 'python@3.8'
# Note: There may be other versions available here: `/System/Library/Frameworks/Python.framework/Versions/`

# unless File.exist? "#{ENV["HOME"]}/.venvburrito/startup.sh"
#   system "curl -sL https://raw.githubusercontent.com/brainsik/virtualenv-burrito/master/virtualenv-burrito.sh | exclude_profile=1 $SHELL"
# end

# debounce { system "virtualenv-burrito upgrade" }

bash_source_relative
