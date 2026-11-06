export PATH="$PATH:$(dirname "${BASH_SOURCE[0]}")/bin"

diff() {
  command diff --color --unified "$@" | diff-pager
}
