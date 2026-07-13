To-do
=====

* Add two new helper methods:
  - `copy`: does similar to `software/download_subtitles/download_subtitles.rb`
  - `sync`: uses `copy` ^^^ and does similar to `software/vlc/vlc.rb`, but ideally uses `FileUtils.cp_r` instead of `FileUtils.copy_file`

* Save secret/private stuff somewhere, somehow (e.g., `~/.ssh`, `~/.aws`, `~/.gnupgp`, `~/.gpg`, etc.)
