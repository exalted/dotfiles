#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby
require_relative '../src/common'
require_relative '../src/helpers'

def apm(package_name)
  system "apm install #{package_name}"
end

cask 'atom'

link 'atom-config.cson', '.atom/config.cson'
link 'atom-init.coffee', '.atom/init.coffee'
link 'atom-keymap.cson', '.atom/keymap.cson'
link 'atom-snippets.cson', '.atom/snippets.cson'
link 'atom-styles.less', '.atom/styles.less'

apm 'highlight-selected'
