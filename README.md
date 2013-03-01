README
======

Get your shit together.

Homebrew
--------

```bash
ruby -e "$(curl -fsSkL raw.github.com/mxcl/homebrew/go)"
```

Git
---

```bash
brew install git
brew install hub
sudo gem install git-up
brew install gibo
sudo gem install svn2git

mkdir -p "$HOME/.config/git"

ln -s "$DEVELOPMENT_DIR/dotfiles/gitconfig.symlink" "$HOME/.config/git/config"
ln -s "$DEVELOPMENT_DIR/dotfiles/gitattributes.symlink" "$HOME/.config/git/attributes"
gibo -u && gibo Django Objective-C Python Archives OSX PyCharm SublimeText SVN > "$HOME/.config/git/ignore"
```

dotfiles
--------

```bash
`# export DEVELOPMENT_DIR="$HOME/Development"`
git clone exalted/dotfiles "$DEVELOPMENT_DIR/dotfiles"
cd "$DEVELOPMENT_DIR/dotfiles"
f() { local DOTFILES=("bash_profile" "bashrc" "inputrc" "sqliterc" "hushlogin"); for i in ${DOTFILES[@]}; do ln -s "$DEVELOPMENT_DIR/dotfiles/$i.symlink" "$HOME/.$i"; done }; f; unset -f f;
```

Fonts and Colors
----------------

### Terminal (OS X)

1. Open Terminal.app and go to Settings tab in application preferences
2. Drag and drop `IR_Black (custom).terminal` file on profiles list section of the window
3. Select "IR_Black (custom)" and click on "Default" button at the bottom of profiles list

### Xcode

```bash
ln -s "$DEVELOPMENT_DIR/dotfiles/Midnight (custom).dvtcolortheme" "$HOME/Library/Developer/Xcode/UserData/FontAndColorThemes/Midnight (custom).dvtcolortheme"
```

Sublime Text 2
--------------

### Use as command line tool

... to open files and projects, as well working as an EDITOR for unix tools, such as git and subversion:

```bash
ln -s "/Applications/Sublime Text 2.app/Contents/SharedSupport/bin/subl" /usr/local/bin/edit
```

### Configure

```bash
ln -s "$DEVELOPMENT_DIR/dotfiles/Preferences.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Preferences.sublime-settings"
ln -s "$DEVELOPMENT_DIR/dotfiles/Package Control.sublime-settings.symlink" "$HOME/Library/Application Support/Sublime Text 2/Packages/User/Package Control.sublime-settings"
```

### Install Sublime Package Control

 1. Open Sublime Text
 2. [Follow these instructions](http://wbond.net/sublime_packages/package_control/installation)
 3. Restart Sublime Text

Utilities
---------

```bash
brew install python
brew install node

brew install rbenv
brew install ruby-build
brew install rbenv-gem-rehash

brew install rmtrash
brew install bash-completion
brew install pwgen

brew install colordiff
brew install grc

sudo gem install liftoff
```

Mark(ed)down
------------

```bash
`# Read first: "Note for rvm/rbenv users" at http://support.markedapp.com/kb/how-to-tips-and-tricks/using-marked-with-github-flavored-markdown-and-syntax-highlighting`
sudo gem install redcarpet pygments.rb
git clone alampros/Docter "$DEVELOPMENT_DIR/Docter"
cd "$DEVELOPMENT_DIR/Docter"
npm --global install
`# Continue here: https://github.com/alampros/Docter#using-with-markedapp`
ln -s "/Applications/Marked.app/Contents/Resources/mark" /usr/local/bin/mark
```

Todo
----

 * Installing gems using `sudo` sucks! How to install in `/usr/local` instead?
