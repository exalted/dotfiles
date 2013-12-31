README
======

Get your shit together
----------------------

```bash
export DEVELOPMENT_DIR="$HOME/Development"
```

Homebrew
--------

```bash
ruby -e "$(curl -fsSkL raw.github.com/mxcl/homebrew/go)"
```

Version Control
---------------

### Install

```bash
brew install git
brew install hub
sudo gem install --verbose --no-rdoc --no-ri git-up
sudo gem install --verbose --no-rdoc --no-ri ghi
brew install gibo
sudo gem install --verbose --no-rdoc --no-ri svn2git
```

### Configure

```bash
mkdir -p "$HOME/.config/git"
mkdir -p "$HOME/.subversion"

ln -s "$DEVELOPMENT_DIR/dotfiles/gitconfig.symlink" "$HOME/.config/git/config"
ln -s "$DEVELOPMENT_DIR/dotfiles/gitattributes.symlink" "$HOME/.config/git/attributes"
gibo -u && gibo OSX Archives SublimeText SVN Tags > "$HOME/.config/git/ignore"

ln -s "$DEVELOPMENT_DIR/dotfiles/subversionconfig.symlink" "$HOME/.subversion/config"
```

Development
-----------

Apply git ignore rules below to each projects' `.gitignore` file.

| Language & Framework |      Git ignore rules      |
| -------------------- | -------------------------- |
| Python & Django      | `Python VirtualEnv Django` |
| Objective-C          | `Objective-C`              |
| Ruby & Rails         | `Ruby Rails`               |

dotfiles
--------

```bash
f() { local DOTFILES=("bash_profile" "bashrc" "inputrc" "sqliterc" "hushlogin" "ackrc" "siegerc"); for i in ${DOTFILES[@]}; do ln -s "$DEVELOPMENT_DIR/dotfiles/$i.symlink" "$HOME/.$i"; done }; f; unset -f f;
```

### Private dotfiles

```bash
f() { local PRIVATE_DOTFILES=("bashrc_private"); for i in ${PRIVATE_DOTFILES[@]}; do ln -s "$HOME/Dropbox/dotfiles/$i.symlink" "$HOME/.$i"; done }; f; unset -f f;
```

SSH
---

```bash
mkdir -p "$HOME/.ssh"

ln -s "$DEVELOPMENT_DIR/dotfiles/sshconfig.symlink" "$HOME/.ssh/config"
```

Sublime Text 2
--------------

### Use as command line tool

... to open files and projects, as well working as an EDITOR for unix tools, such as git and subversion:

```bash
ln -s "/Applications/Sublime Text 2.app/Contents/SharedSupport/bin/subl" /usr/local/bin/subl
```

### Configure

#### Application

```bash
ln -s "$DEVELOPMENT_DIR/dotfiles/Default (OSX).sublime-keymap.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Default (OSX).sublime-keymap"
ln -s "$DEVELOPMENT_DIR/dotfiles/Preferences.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Preferences.sublime-settings"
```

#### Themes

```bash
ln -s "$DEVELOPMENT_DIR/dotfiles/Espresso Soda.tmTheme.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Espresso Soda.tmTheme"
ln -s "$DEVELOPMENT_DIR/dotfiles/Monokai Soda.tmTheme.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Monokai Soda.tmTheme"
```

#### Requirements

```bash
brew install ctags
cat <<EOF >> "$HOME/.config/git/ignore"
# Ignore tags created by ctags
.tags
.tags_sorted_by_file
.gemtags


EOF
```

If you are a Rubyist, you can build a Ruby Gem's tags with the following script:

```ruby
# (Ref.: https://github.com/SublimeText/CTags/blob/master/README.creole#usage)
require 'bundler'
paths = Bundler.load.specs.map(&:full_gem_path)
system("ctags -R -f .gemtags #{paths.join(' ')}")
```

#### Packages

```bash
ln -s "$DEVELOPMENT_DIR/dotfiles/GitGutter.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/GitGutter.sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/Package Control.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Package Control.sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/SublimeLinter.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/SublimeLinter.sublime-settings"
```

#### Syntax Specific

```bash
ln -s "$DEVELOPMENT_DIR/dotfiles/CoffeeScript.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/CoffeeScript.sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/Find Results.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Find Results.sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/HTML (Rails).sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/HTML (Rails).sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/JSON.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/JSON.sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/RSpec.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/RSpec.sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/Ruby on Rails.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Ruby on Rails.sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/Ruby.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Ruby.sublime-settings"
```

### Install Sublime Package Control

 1. Open Sublime Text
 2. [Follow these instructions](http://wbond.net/sublime_packages/package_control/installation)
 3. Restart Sublime Text

### Plugins to Install Without Package Control

 1. [Install Rails Snippets](https://github.com/tadast/sublime-rails-snippets/#readme) ([Why?](https://github.com/tadast/sublime-rails-snippets/issues/8))

Objective-C
-----------

```bash
sudo gem install --verbose --no-rdoc --no-ri cocoapods
pod setup
```

Python
------

```bash
brew install python
curl -s https://raw.github.com/brainsik/virtualenv-burrito/master/virtualenv-burrito.sh | exclude_profile=1 $SHELL
```

Ruby
----

### Install

Read more: https://github.com/sstephenson/ruby-build/wiki#installing-200-p195-on-osx-107

```bash
brew install openssl
brew install readline
brew install rbenv
brew install ruby-build
brew install rbenv-gem-rehash
brew install rbenv-vars
brew install rbenv-default-gems
```

### Configure

```bash
mkdir -p "$HOME/.rbenv"

ln -s "$DEVELOPMENT_DIR/dotfiles/default-gems.symlink" "$HOME/.rbenv/default-gems"
```

### Install a Ruby

```bash
export CFLAGS=-Wno-error=shorten-64-to-32
env RUBY_CONFIGURE_OPTS=--with-openssl-dir=`brew --prefix openssl` CONFIGURE_OPTS=--with-readline-dir=`brew --prefix readline` rbenv install 2.0.0-p195
```

Node
----

```bash
brew install node
```

Utilities
---------

```bash
brew install bash-completion

brew install grc
brew install jsonpp
brew install graphviz

brew install rmtrash
brew install pwgen

brew install wget
sudo pip install --upgrade httpie
brew install siege && sudo sysctl -w net.inet.tcp.msl=1000

sudo gem install --verbose --no-rdoc --no-ri liftoff

mkdir /usr/local/ThirdParty; cd $_
curl -fsSkL https://github.com/paulhammond/jp/releases/download/v0.1/jp-0.1-darwin-x86_64.tar.gz | tar xfz -
ln -s /usr/local/ThirdParty/jp-0.1/jp /usr/local/bin/jp
```

Fonts and Colors
----------------

### Terminal (OS X)

1. Open Terminal.app and go to Settings tab in application preferences
2. Drag and drop `IR_Black (custom).terminal` file on profiles list section of the window
3. Select "IR_Black (custom)" and click on "Default" button at the bottom of profiles list

### Xcode

```bash
mkdir -p "$HOME/Library/Developer/Xcode/UserData/FontAndColorThemes"

ln -s "$DEVELOPMENT_DIR/dotfiles/Midnight (custom).dvtcolortheme" "$HOME/Library/Developer/Xcode/UserData/FontAndColorThemes/Midnight (custom).dvtcolortheme"
```

Mark(ed)down
------------

Read first: "Note for rvm/rbenv users" at http://support.markedapp.com/kb/how-to-tips-and-tricks/using-marked-with-github-flavored-markdown-and-syntax-highlighting

```bash
sudo gem install --verbose --no-rdoc --no-ri redcarpet
sudo gem install --verbose --no-rdoc --no-ri pygments.rb
git clone alampros/Docter "$DEVELOPMENT_DIR/Docter"
cd "$DEVELOPMENT_DIR/Docter"
npm --global install
ln -s "/Applications/Marked.app/Contents/Resources/mark" /usr/local/bin/mark
```

Continue here: https://github.com/alampros/Docter#using-with-markedapp

Configure Sublime Text with "Marked Bonus Pack" (available here: http://support.markedapp.com/kb/how-to-tips-and-tricks/marked-bonus-pack-scripts-commands-and-bundles)

```bash
ln -s "$DEVELOPMENT_DIR/dotfiles/Marked.sublime-build.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Marked.sublime-build"
```

Mail
----

```bash
defaults write com.apple.mail SuppressAddressHistory -bool true
```

Finder
------

```bash
defaults write com.apple.desktopservices DSDontWriteNetworkStores true
defaults write com.apple.finder QLEnableTextSelection -bool true
killall Finder
```

Dictionary
----------

```bash
ln -s "$DEVELOPMENT_DIR/dotfiles/com.apple.Dictionary.plist.symlink" "$HOME/Library/Preferences/com.apple.Dictionary.plist"

mkdir -p "$HOME/Library/Dictionaries/"

ln -s "$DEVELOPMENT_DIR/dotfiles/italian.dictionary" "$HOME/Library/Dictionaries/italian.dictionary"
```

CUPS
----

Turn on the Mac's web interface for its CUPS server:

```bash
sudo cupsctl WebInterface=yes
```

Local printer configuration web page: `http://localhost:631/admin`.

Todo
----

* Installing gems using `sudo` sucks! (I could install with `rbenv`, but that's a problem for Marked.app: see ["Note for rvm/rbenv users"](http://support.markedapp.com/kb/how-to-tips-and-tricks/using-marked-with-github-flavored-markdown-and-syntax-highlighting))
* Replace "hushlogin" with http://apple.stackexchange.com/questions/31872/how-do-i-reset-the-scrollback-in-the-terminal-via-a-shell-command.
* ~~Add best-practice alises for git CLI~~
* Replace most of the `mkdir`s in this file by symlinking to that directory instead (For private files/folders symlink to `~/Dropbox/dotfiles/` instead)
* Create `script/bootstrap` that you could run over and over again which would install or setup what's missing automagically or do nothing if everything is just in place
* Checkout [legit](https://github.com/kennethreitz/legit) which *could* replace current git aliases
* ~~Symlink to`~/.pow` and `~/Library/Application\ Support/Pow/Hosts` (for Pow.cx, Anvil, etc.)~~
* Hard-coded rbenv path [sucks](https://github.com/exalted/dotfiles/blob/1be30f7112c8b5370b9f48d4d69c4df8bc2dd1ff/SublimeLinter.sublime-settings.symlink#L3)
* Set `Terminal.app`'s window (or better: tab?) title to whatever command name that is running at that moment (e.g., "foreman start", "script/start", "guard", etc.). Resources: [1](http://hints.macworld.com/dlfiles/preexec.bash.txt), [2](http://thelucid.com/2012/01/04/naming-your-terminal-tabs-in-osx-lion/), [3](http://dan.doezema.com/2013/04/programmatically-create-title-tabs-within-the-mac-os-x-terminal-app/), [4](http://stackoverflow.com/questions/4197441/get-name-of-last-run-program-in-bash), [5](http://unix.stackexchange.com/questions/33794/how-can-i-alias-to-last-command), [6](http://superuser.com/questions/117227/a-command-before-every-bash-command), [7](http://stackoverflow.com/questions/4585397/bash-run-some-command-before-or-after-every-command-entered-from-console)
* Improve git alias `live-log` with [watchng](https://github.com/lpenz/watchng/)
