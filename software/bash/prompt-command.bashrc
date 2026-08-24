# Shared helpers for registering prompt hooks.
#
# PROMPT_COMMAND is a single string, so every fragment that wants a prompt hook
# (shared history, blank lines, nvm auto-use, direnv) has to read-modify-write
# the same variable. Without a common convention that stacks up: re-sourcing
# ~/.bashrc, or opening a nested interactive Bash, appends every hook a second
# time and each one then runs twice per prompt.
#
# Two rules make that safe, and these helpers encode both:
#
#   1. Register by function name and bail out if it is already there.
#   2. Join entries with a bare `;` and no space. direnv's own hook installs
#      itself with the same convention and skips itself when it finds
#      `;_direnv_hook;` in PROMPT_COMMAND — a space after the separator would
#      defeat that guard and re-add direnv on every re-source.
#
# PROMPT_COMMAND is deliberately *not* exported. It names shell functions, and
# functions aren't exported either, so a child shell that skips ~/.bashrc (e.g.
# `bash --norc -i`) would inherit the names but not the definitions and print
# "command not found" before every prompt.
#
# Enforced, not just documented: the export attribute survives a plain
# reassignment, so any shell descended from one started before this file existed
# (history.bashrc used to `export PROMPT_COMMAND=…`) would keep exporting ours.
# `export -n` on an unset variable is a no-op, so this is safe to run always.
export -n PROMPT_COMMAND

__prompt_command_has() {
  # `; ` as well as `;` — that's how the pre-helpers fragments joined entries,
  # and their value is still what a child of any shell started before this file
  # existed inherits. Missing it there re-adds the hook, so it runs twice.
  case ";${PROMPT_COMMAND:-};" in
    *";$1;"* | *"; $1;"*) return 0 ;;
    *) return 1 ;;
  esac
}

# Run before the hooks registered so far.
__prompt_command_prepend() {
  __prompt_command_has "$1" && return 0
  PROMPT_COMMAND="$1${PROMPT_COMMAND:+;$PROMPT_COMMAND}"
}

# Run after the hooks registered so far.
__prompt_command_append() {
  __prompt_command_has "$1" && return 0
  PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND;}$1"
}
