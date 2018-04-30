#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'tmux'

link_to_home_relative 'conf', '.tmux.conf'

bash_source_relative

# TODO: consider enabling this as the last line of your ~/.bashrc
# if [ "$TMUX" = "" ]; then exec tmux; fi


# TODO: consider improving your tmux:
#
# From thoughtbot:
#https://robots.thoughtbot.com/love-hate-tmux
#https://robots.thoughtbot.com/a-tmux-crash-course
#https://robots.thoughtbot.com/how-to-copy-and-paste-with-tmux-on-mac-os-x
#https://robots.thoughtbot.com/seamlessly-navigate-vim-and-tmux-splits
#https://robots.thoughtbot.com/tmux-copy-paste-on-os-x-a-better-future
#https://robots.thoughtbot.com/running-specs-from-vim-sent-to-tmux-via-tslime
#https://robots.thoughtbot.com/use-rspec-vim-with-tmux-and-dispatch
#https://robots.thoughtbot.com/tmux-only-for-long-running-processes
#https://robots.thoughtbot.com/announcing-the-tmux-course-on-upcase
#https://robots.thoughtbot.com/migrating-from-screen-to-tmux
#
#https://sanctum.geek.nz/arabesque/tag/tmux-conf/
#https://sanctum.geek.nz/arabesque/category/tmux/
#
# Create new-window with current directory in tmux
#https://unix.stackexchange.com/questions/12032/create-new-window-with-current-directory-in-tmux
#
# Better mouse scrolling in Tmux
#http://www.davidverhasselt.com/better-mouse-scrolling-in-tmux/
#
# https://medium.freecodecamp.org/tmux-in-practice-series-of-posts-ae34f16cfab0
