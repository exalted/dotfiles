dotfiles
========

This assumes your shell of choice is Bash.

## Install dotfiles

Paste the following to a Terminal prompt:

```bash
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/exalted/dotfiles/master/install)"
```

## Usage

Whenever you feel like, run a simple command to keep your environment up-to-date:

```bash
dotfiles
```

## How to add new software

0. Create a script file anywhere (also in a nested directory) inside `software/` (e.g., `software/example.rb`). (Not necessarily in Ruby, but encouraged. Shell/Python/JavaScript are also welcome.)
0. Make sure it's executable (`chmod +x software/example.rb`).
0. Make sure it has correct shebang (e.g., `#!/System/Library/Frameworks/Ruby.framework/Versions/Current/usr/bin/ruby` for Ruby, `#!/bin/sh` for Shell, etc.).
0. Make sure they're self executable, meaning they work even if you run them directly like `./software/example.rb` rather than through `bin/dotfiles`.
0. Try to write your script as less order dependent as possible related to order software.
