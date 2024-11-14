#!/usr/bin/env ruby
require_relative '../../src/helpers'

brew 'git'
brew 'git-lfs'
brew 'gh'
# brew 'hub'  # See https://hub.github.com/hub.1.html
brew 'git-extras'  # See https://github.com/tj/git-extras/blob/main/Commands.md

link_to_home_relative 'config', '.config/git/config'
link_to_home_relative 'attributes', '.config/git/attributes'

bash_source_relative

gitignore_templates = %w[
  Global/macOS.gitignore
  Global/Archives.gitignore
  Global/Dropbox.gitignore
  Global/Emacs.gitignore
  Global/VisualStudioCode.gitignore
  Global/Xcode.gitignore
]

FileUtils.mkdir_p "#{ENV["HOME"]}/.config/git"
system "> #{ENV["HOME"]}/.config/git/ignore"

gitignore_templates.each do |template|
  template_url = "https://raw.githubusercontent.com/github/gitignore/refs/heads/main/#{template}"
  File.open("#{ENV["HOME"]}/.config/git/ignore", 'a') { |f| f.puts "### #{template_url}" }
  system("curl -fsSL #{template_url} >> #{ENV["HOME"]}/.config/git/ignore")
end

File.open("#{ENV["HOME"]}/.config/git/ignore", 'a') do |f|
  f << <<-EOF
### MY CUSTOM RULES
.editorconfig
EOF
end
