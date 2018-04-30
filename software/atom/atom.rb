#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../../src/helpers'

cask 'atom'

link_to_home_relative 'config.cson', '.atom/config.cson'
link_to_home_relative 'init.coffee', '.atom/init.coffee'
link_to_home_relative 'keymap.cson', '.atom/keymap.cson'
link_to_home_relative 'snippets.cson', '.atom/snippets.cson'
link_to_home_relative 'styles.less', '.atom/styles.less'

bash_source_relative

module APM
  def self.install(package_name)
    return if Kernel.system "apm list --bare --installed | cut -f 1 -d@ -s | grep ^#{package_name}$ > /dev/null"
    Kernel.system "apm install #{package_name}"
  end
end

# Stuff (sorted)
APM.install 'atom-ide-ui'
APM.install 'center-line'
APM.install 'cursor-history'
APM.install 'editorconfig'
APM.install 'emmet'
APM.install 'highlight-selected'
APM.install 'ide-html'
APM.install 'multi-cursor'
APM.install 'sort-lines'

# IDEA: should these be placed inside specific software/* instead?
#       For instance `APM.install 'language-docker'` could be moved into
#       `software/docker.rb`, or `APM.install 'language-babel'` and
#       `APM.install 'linter-eslint'` into `languages/javascript.rb` (which
#       doesn't exist yet, but you should consider…)
#
#       Better (?) idea: each `software/*` (and eventually `languages/*`) script
#       can call a helper method, say `apm_package` (or simply `apm`), which this
#       script (`atom.rb`) can search for every occurrence of, and install.
#
#       Why? Because, `software/*` is run in no particular order, so `apm` may
#       not be still available for some `software/*`, so either they would break
#       or apm packages may not be installed after `dotfiles` is run. (We could
#       make a special install case for `apm`, thus Atom [similar to `brew` and
#       `mas`], but I don't think it's system-wide enough to deserve it.)

# JavaScript development
APM.install 'ide-typescript' # TypeScript and Javascript language support for Atom-IDE
APM.install 'language-babel'
APM.install 'linter-eslint'

# Docker
APM.install 'language-docker'
