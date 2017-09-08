dotfiles
========

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

## Add new software

1. Create a script file in `software/` (not necessarily in Ruby, but encouraged)
2. Make sure it's executable (`chmod +x`)
3. Try to make sure it is as much order independent as possible related to order software
