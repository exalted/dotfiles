#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

brew 'git'
brew 'git-lfs'
brew 'gh'
brew 'hub'
brew 'git-extras'
brew 'gibo'  # TODO: consider https://www.gitignore.io instead

link_to_home_relative 'config', '.config/git/config'
link_to_home_relative 'attributes', '.config/git/attributes'

bash_source_relative

globalignore_boilerplates = %w[ macOS Archives Dropbox Emacs VisualStudioCode Xcode ]
FileUtils.mkdir_p "#{ENV["HOME"]}/.config/git"
system(
  "gibo dump #{globalignore_boilerplates.join(' ')} "\
  "> #{ENV["HOME"]}/.config/git/ignore"
)
# File.open("#{ENV["HOME"]}/.config/git/ignore", 'a') do |f|
#   f << <<-EOF
# ### MY CUSTOM RULES
# .editorconfig
# EOF
# end
