To-do
=====

* When `dotfiles` is run, it should update it self via `git pull` or similar
  - WARNING: some programs may have modified linked config files underneath, so think about a good strategy to avoid merge conflicts (I believe homebrew does something to avoid this in 4 steps in their install script)

* Check all the `TODO`s and `NOTE`s, everywhere!

* Open all `software/**/*` and see if something is missing/off/not-right

* Consider https://github.com/sorah/envchain for secure environment variables or `security` command (https://www.netmeister.org/blog/keychain-passwords.html)

* Import text replace shortcuts/rules
  - You can check https://github.com/warpling/Macmoji/blob/master/scripts/macmoji to see how they read/write from/to macOS text replacements
  - Is this really necessary? iCloud already saves to cloud and syncs them with your other devices… (?)

* Bunch of Bash goodies here: http://kvz.io/blog/2013/11/21/bash-best-practices/

* watch file(system) changes
  - https://facebook.github.io/watchman/
  - https://github.com/mattgreen/watchexec
  - https://github.com/emcrisostomo/fswatch

* gem install terminal-emojify

* ```bash
  brew install emacs
  ln -sfv /usr/local/opt/emacs/*.plist ~/Library/LaunchAgents
  launchctl load "$HOME/Library/LaunchAgents/homebrew.mxcl.emacs.plist"
  ```
