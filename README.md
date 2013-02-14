README
======

Get your shit together.

Homebrew
--------

```bash
$ ruby -e "$(curl -fsSkL raw.github.com/mxcl/homebrew/go)"
$ brew install brew-gem
```

Git
---

```bash
$ brew install git
$ brew install hub
$ brew install gibo
`# $ brew install svn2git	`# installed via brew-gem``

$ gibo -u
$ gibo Django Objective-C Python Archives OSX PyCharm SublimeText SVN > .gitignore_global
```

dotfiles
--------

```bash
`# export DEVELOPMENT_DIR="$HOME/Development"`
$ git clone exalted/dotfiles "$DEVELOPMENT_DIR/dotfiles"
$ cd "$DEVELOPMENT_DIR/dotfiles"
$ f() { local DOTFILES=("bash_profile" "bashrc" "gitconfig" "inputrc" "sqliterc" "hushlogin"); for i in ${DOTFILES[@]}; do ln -s "$DEVELOPMENT_DIR/dotfiles/$i.symlink" "$HOME/.$i"; done }; f; unset -f f;
```

Fonts and Colors
----------------

### Terminal (OS X)

1. Open Terminal.app and go to Settings tab in application preferences
2. Drag and drop `IR_Black (custom).terminal` file on profiles list section of the window
3. Select "IR_Black (custom)" and click on "Default" button at the bottom of profiles list

### Xcode

```bash
$ ln -s "$DEVELOPMENT_DIR/dotfiles/Midnight\ \(custom\).dvtcolortheme" "$HOME/Library/Developer/Xcode/UserData/FontAndColorThemes/Midnight\ \(custom\).dvtcolortheme"
```

Use Sublime Text 2 command line tool
------------------------------------

... to open files and projects2, as well working as an EDITOR for unix tools,
such as git and subversion:

```bash
$ ln -s /Applications/Sublime\ Text\ 2.app/Contents/SharedSupport/bin/subl /usr/local/bin/sublime
```

Utilities
---------

```bash
$ brew install python `# Depends on: pkg-config, readline, sqlite, gdbm`
$ brew install node

$ brew install rmtrash
$ brew install bash-completion
$ brew install pwgen

$ brew install colordiff
$ brew install grc
```

Markdown
--------

```bash
$ sudo gem install redcarpet pygments.rb `# Read "Note for rvm/rbenv users" at http://support.markedapp.com/kb/how-to-tips-and-tricks/using-marked-with-github-flavored-markdown-and-syntax-highlighting`
$ git clone alampros/Docter "$DEVELOPMENT_DIR/Docter"
$ cd "$DEVELOPMENT_DIR/Docter"
$ npm --global install
`# Continue here: https://github.com/alampros/Docter#using-with-markedapp`
```
