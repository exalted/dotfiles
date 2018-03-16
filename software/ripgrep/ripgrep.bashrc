grep() {
  echo -e 'grep: Consider using `rg` command instead…\n'
  command grep "$@"
}
