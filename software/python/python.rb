#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'python@2'
brew 'python'    # this is the latest and greatest

# unless File.exist? "#{ENV["HOME"]}/.venvburrito/startup.sh"
#   Kernel.system "curl -sL https://raw.githubusercontent.com/brainsik/virtualenv-burrito/master/virtualenv-burrito.sh | exclude_profile=1 $SHELL"
# end

# debounce { Kernel.system "virtualenv-burrito upgrade" }

# bash_source_relative
