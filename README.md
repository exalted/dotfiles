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
gibo -u && gibo Django Objective-C Python Archives OSX PyCharm SublimeText SVN Ruby Rails > "$HOME/.config/git/ignore"

ln -s "$DEVELOPMENT_DIR/dotfiles/subversionconfig.symlink" "$HOME/.subversion/config"
```

dotfiles
--------

```bash
f() { local DOTFILES=("bash_profile" "bashrc" "inputrc" "sqliterc" "hushlogin" "gemrc"); for i in ${DOTFILES[@]}; do ln -s "$DEVELOPMENT_DIR/dotfiles/$i.symlink" "$HOME/.$i"; done }; f; unset -f f;
`# Private dotfiles:`
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

```bash
ln -s "$DEVELOPMENT_DIR/dotfiles/Preferences.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Preferences.sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/Default (OSX).sublime-keymap.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Default (OSX).sublime-keymap"
ln -s "$DEVELOPMENT_DIR/dotfiles/Package Control.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Package Control.sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/GitGutter.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/GitGutter.sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/Monokai Soda.tmTheme.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Monokai Soda.tmTheme"
ln -s "$DEVELOPMENT_DIR/dotfiles/Espresso Soda.tmTheme.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Espresso Soda.tmTheme"
ln -s "$DEVELOPMENT_DIR/dotfiles/Ruby.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Ruby.sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/Ruby on Rails.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Ruby on Rails.sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/ApplySyntax.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/ApplySyntax.sublime-settings"
`# Marked Bonus Pack available here: http://support.markedapp.com/kb/how-to-tips-and-tricks/marked-bonus-pack-scripts-commands-and-bundles`
ln -s "$DEVELOPMENT_DIR/dotfiles/Marked.sublime-build.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Marked.sublime-build"
```

### Install Sublime Package Control

 1. Open Sublime Text
 2. [Follow these instructions](http://wbond.net/sublime_packages/package_control/installation)
 3. Restart Sublime Text

Python
------

```bash
brew install python
curl -s https://raw.github.com/brainsik/virtualenv-burrito/master/virtualenv-burrito.sh | exclude_profile=1 $SHELL
```

Ruby
----

### Install

```bash
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

brew install rmtrash
brew install pwgen

brew install wget
sudo pip install --upgrade httpie

sudo gem install --verbose --no-rdoc --no-ri liftoff
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

```bash
`# Read first: "Note for rvm/rbenv users" at http://support.markedapp.com/kb/how-to-tips-and-tricks/using-marked-with-github-flavored-markdown-and-syntax-highlighting`
sudo gem install --verbose --no-rdoc --no-ri redcarpet
sudo gem install --verbose --no-rdoc --no-ri pygments.rb
git clone alampros/Docter "$DEVELOPMENT_DIR/Docter"
cd "$DEVELOPMENT_DIR/Docter"
npm --global install
ln -s "/Applications/Marked.app/Contents/Resources/mark" /usr/local/bin/mark
`# Continue here: https://github.com/alampros/Docter#using-with-markedapp`
```

Todo
----

 1. Installing gems using `sudo` sucks! (I could install with `rbenv`, but that's a problem for Marked.app: see ["Note for rvm/rbenv users"](http://support.markedapp.com/kb/how-to-tips-and-tricks/using-marked-with-github-flavored-markdown-and-syntax-highlighting))
 2. Replace "hushlogin" with http://apple.stackexchange.com/questions/31872/how-do-i-reset-the-scrollback-in-the-terminal-via-a-shell-command.
 3. Add best-practice alises for git CLI
