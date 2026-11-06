# Zed's Ruby extension complain unless the "system" ruby isn't >=2.7 and macOS ruby is currently `ruby 2.6.10p210 (2022-04-12 revision 67958) [universal.arm64e-darwin24]`, hence giving priority to Homebrew installed Ruby:
export PATH="$(brew --prefix)/opt/ruby/bin:$PATH"

#
# Ruby version manager
#
eval "$(rbenv init -)"
