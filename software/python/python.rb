#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'python@3.8'  # this is the version I set as "default" in my system (see `software/python/bashrc`)
brew 'python@3.9'

# unless File.exist? "#{ENV["HOME"]}/.venvburrito/startup.sh"
#   Kernel.system "curl -sL https://raw.githubusercontent.com/brainsik/virtualenv-burrito/master/virtualenv-burrito.sh | exclude_profile=1 $SHELL"
# end

# debounce { Kernel.system "virtualenv-burrito upgrade" }

# bash_source_relative
