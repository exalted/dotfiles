function env-wrapper {
  if [[ -z "$@" ]]; then
    # When "printing the environment" I usually want to see all variables defined
    # and not just those that are `export`-ed; so this takes care of that when
    # `env` used without additional options.
    # https://unix.stackexchange.com/a/118050
    (set -o posix; set)
  else
    command env "$@"
  fi
}

# `alias` takes precedence over functions, built-ins, and $PATH
alias env='env-wrapper'
