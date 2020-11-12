To-do
=====

* When `dotfiles` is run, it should update it self via `git pull` or similar
  - WARNING: some programs may have modified linked config files underneath, so think about a good strategy to avoid merge conflicts (I believe homebrew does something to avoid this in 4 steps in their install script)

* Add two new helper methods:
  - `copy`: does similar to `software/download_subtitles/download_subtitles.rb`
  - `sync`: uses `copy` ^^^ and does similar to `software/mosaic/mosaic.rb` and `software/vlc/vlc.rb`, but ideally uses `FileUtils.cp_r` instead of `FileUtils.copy_file`

* Save secret/private stuff somewhere/somehow `~/.ssh`, `~/.aws`, `~/.gnupgp`, `~/.gpg`, etc.
  - Consider https://github.com/sorah/envchain for secure environment variables or `security` command (https://www.netmeister.org/blog/keychain-passwords.html)
