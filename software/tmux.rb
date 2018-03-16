#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../src/helpers'

brew 'tmux'

# TODO: enabled this as the last line of your ~/.bashrc
# if [ "$TMUX" = "" ]; then exec tmux; fi
