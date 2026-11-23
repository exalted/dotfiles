_codex_starts_session() {
  [[ $- == *i* && -t 0 && -t 1 ]] || return 1

  case "${1:-}" in
    exec|e|review|login|logout|mcp|plugin|app-server|remote-control|app|completion|update|doctor|sandbox|debug|apply|a|queue|archive|delete|migrate-rollouts|migrate-nfs-db|unarchive|cloud|exec-server|features|help) return 1 ;;
  esac

  local arg
  for arg in "$@"; do
    case "$arg" in
      -h|--help|-V|--version) return 1 ;;
    esac
  done
}

codex() {
  _codex_starts_session "$@" && upgrade-cask-daily codex
  command codex "$@"
}
