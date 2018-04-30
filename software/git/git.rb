#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'git'
brew 'hub'
brew 'git-extras'
brew 'gibo'  # TODO: consider https://www.gitignore.io instead

link_to_home_relative 'config', '.config/git/config'
link_to_home_relative 'attributes', '.config/git/attributes'

bash_source_relative

globalignore_boilerplates = %w[ macOS Archives Dropbox Emacs Xcode ]
Kernel.system(
  "mkdir -p #{ENV["HOME"]}/.config/git && "\
  "gibo #{globalignore_boilerplates.join(' ')} "\
  "> #{ENV["HOME"]}/.config/git/ignore"
)
