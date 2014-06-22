README
======

First things first.

```bash
export DEVELOPMENT_DIR="$HOME/Development"
```

Install the :shit:
------------------

```bash
ruby -e "$(curl -fsSkL raw.github.com/mxcl/homebrew/go)"
```

Upgrade Ruby
------------

### Install rbenv

```bash
brew install rbenv
brew install ruby-build
brew install rbenv-gem-rehash
```

### Install and override system Ruby

```bash
export __RUBY_VERSION__='2.0.0-p247'
```

Why bother with openssl below? [Because](https://github.com/sstephenson/ruby-build/wiki#installing-200-p195-on-osx-107).

```bash
brew install openssl
brew install readline
export CFLAGS=-Wno-error=shorten-64-to-32
env RUBY_CONFIGURE_OPTS=--with-openssl-dir=`brew --prefix openssl` CONFIGURE_OPTS=--with-readline-dir=`brew --prefix readline` rbenv install "$__RUBY_VERSION__"
rbenv global "$__RUBY_VERSION__"
```

dotfiles
--------

```bash
f() { local DOTFILES=("bash_profile" "bashrc" "inputrc" "sqliterc" "hushlogin" "ackrc" "siegerc" "gemrc" "rspec"); for i in ${DOTFILES[@]}; do ln -s "$DEVELOPMENT_DIR/dotfiles/$i.symlink" "$HOME/.$i"; done }; f; unset -f f;
```

### Secrets

```bash
f() { local PRIVATE_DOTFILES=("bashrc_private"); for i in ${PRIVATE_DOTFILES[@]}; do ln -s "$HOME/Dropbox/dotfiles/$i.symlink" "$HOME/.$i"; done }; f; unset -f f;
```

Git
---

### Install

```bash
brew install git
brew install hub
brew install gibo
gem install --no-document --verbose svn2git
```

### Configure

```bash
mkdir -p "$HOME/.config/git"
mkdir -p "$HOME/.subversion"

ln -s "$DEVELOPMENT_DIR/dotfiles/gitconfig.symlink" "$HOME/.config/git/config"
ln -s "$DEVELOPMENT_DIR/dotfiles/gitattributes.symlink" "$HOME/.config/git/attributes"
gibo -u && gibo OSX Archives SublimeText SVN > "$HOME/.config/git/ignore"

ln -s "$DEVELOPMENT_DIR/dotfiles/subversionconfig.symlink" "$HOME/.subversion/config"
```

Development
-----------

### gitignore

Note: Keep a project’s root level `.gitignore` file with up–to–date rules using `gibo` and add project–specific rules in separate `.gitignore` files. (`git` is absolutely okay with that.)

Although they might already be globally ignored, play safe and add the following git ignore rules in every project:

```bash
gibo -u && gibo OSX Archives SublimeText > .gitignore
```

Also, append the relevant git ignore rules to each projects’ `.gitignore` file:

| Language & Framework | Git ignore rules                                         |
| -------------------- | -------------------------------------------------------- |
| Ruby & Rails         | `gibo -u && gibo Ruby Rails >> .gitignore`               |
| Objective-C          | `gibo -u && gibo Objective-C >> .gitignore`              |
| Python & Django      | `gibo -u && gibo Python VirtualEnv Django >> .gitignore` |

### Ruby

Install Pry:

```bash
gem install --no-document --verbose pry pry-doc
```

Additional plugins for Pry:

```bash
gem install --no-document --verbose pry-coolline
```

### Objective-C

```bash
gem install --no-document --verbose cocoapods
pod setup
```

### Python

```bash
brew install python
curl -s https://raw.github.com/brainsik/virtualenv-burrito/master/virtualenv-burrito.sh | exclude_profile=1 $SHELL
```

### Node

```bash
brew install node
```

### Go

```bash
brew install go
mkdir -p "$DEVELOPMENT_DIR/go"
```

### Utilities

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

mkdir /usr/local/ThirdParty; cd $_
curl -fsSkL https://github.com/paulhammond/jp/releases/download/v0.1/jp-0.1-darwin-x86_64.tar.gz | tar xfz -
ln -s /usr/local/ThirdParty/jp-0.1/jp /usr/local/bin/jp
```

Atom
----

```bash
brew install mercurial
go get -u github.com/shurcooL/markdownfmt
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

#### Packages

```bash
ln -s "$DEVELOPMENT_DIR/dotfiles/GitGutter.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/GitGutter.sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/Package Control.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Package Control.sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/SublimeLinter.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/SublimeLinter.sublime-settings"
```

### Install Sublime Package Control

 1. Open Sublime Text
 2. [Follow these instructions](http://wbond.net/sublime_packages/package_control/installation)
 3. Restart Sublime Text

### Plugins to Install Without Package Control

 1. [Install Rails Snippets](https://github.com/tadast/sublime-rails-snippets/#readme) ([Why?](https://github.com/tadast/sublime-rails-snippets/issues/8))

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

Turn on the Mac’s web interface for its CUPS server:

```bash
sudo cupsctl WebInterface=yes
```

Local printer configuration web page: `http://localhost:631/admin`.

SSH
---

```bash
mkdir -p "$HOME/.ssh"

ln -s "$DEVELOPMENT_DIR/dotfiles/sshconfig.symlink" "$HOME/.ssh/config"
```

### Create a new key

```bash
ssh-keygen -t rsa -C "$(whoami)@$(hostname)" -f "$HOME/.ssh/foobar_rsa"
```

### Upload keys to Heroku

```bash
heroku keys:add "$HOME/.ssh/foobar_rsa.pub"
```

Todo
----

* Installing gems using `sudo` sucks! ~~(I could install with `rbenv`, but that’s a problem for Marked.app: see ["Note for rvm/rbenv users"](http://support.markedapp.com/kb/how-to-tips-and-tricks/using-marked-with-github-flavored-markdown-and-syntax-highlighting))~~
* Replace "hushlogin" with http://apple.stackexchange.com/questions/31872/how-do-i-reset-the-scrollback-in-the-terminal-via-a-shell-command.
* Replace most of the `mkdir`s in this file by symlinking to that directory instead (For private files/folders symlink to `~/Dropbox/dotfiles/` instead)
* Create `script/bootstrap` that you could run over and over again which would install or setup what’s missing automagically or do nothing if everything is just in place
* ~~Symlink to`~/.pow` and `~/Library/Application\ Support/Pow/Hosts` (for Pow.cx, Anvil, etc.)~~
* Hard-coded rbenv path [sucks](https://github.com/exalted/dotfiles/blob/1be30f7112c8b5370b9f48d4d69c4df8bc2dd1ff/SublimeLinter.sublime-settings.symlink#L3)
* Set `Terminal.app`’s window (or better: tab?) title to whatever command name that is running at that moment (e.g., "foreman start", "script/start", "guard", etc.). Resources: [1](http://hints.macworld.com/dlfiles/preexec.bash.txt), [2](http://thelucid.com/2012/01/04/naming-your-terminal-tabs-in-osx-lion/), [3](http://dan.doezema.com/2013/04/programmatically-create-title-tabs-within-the-mac-os-x-terminal-app/), [4](http://stackoverflow.com/questions/4197441/get-name-of-last-run-program-in-bash), [5](http://unix.stackexchange.com/questions/33794/how-can-i-alias-to-last-command), [6](http://superuser.com/questions/117227/a-command-before-every-bash-command), [7](http://stackoverflow.com/questions/4585397/bash-run-some-command-before-or-after-every-command-entered-from-console)
* Kinda better [`{dot/rc}files` management](http://robots.thoughtbot.com/rcm-for-rc-files-in-dotfiles-repos)?

### Git(Hub) related

* ~~Add best-practice alises for git CLI~~
* Checkout [legit](https://github.com/kennethreitz/legit) which *could* replace current git aliases
* Improve git alias `live-log` with [watchng](https://github.com/lpenz/watchng/)
* [Compare Commits Between Git Branches](http://robots.thoughtbot.com/compare-commits-between-git-branches)
* [gitver](http://onethingwell.org/post/72550558317/gitver)
* [a simple git branching model](https://gist.github.com/jbenet/ee6c9ac48068889b0912)
* Don’t rebase a feature branch from `master` once it’s published
* To avoid merge bubbles you _may_ rebase a feature branch **only** prior to "merging" it into `master`
* Merge to `master` **always** with `--no-ff`
* Use _maybe_ [git_pretty_accept](https://github.com/lovewithfood/git_pretty_accept), or *maybe not* ;-)
