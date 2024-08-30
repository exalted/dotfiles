# TODO: Add a case for grep installed via homebrew (ie ggrep), because `man grep`
#       will not found nothing, but `man ggrep` does (do also for `fgrep` and `egrep`
#       to open `man ggrep`)

# (Ref.: http://unix.stackexchange.com/a/18088)
function man {
  case "$(type -t "$1"):$1" in
    builtin:* )
      # built-in
      help "$1" | "${PAGER:-less}"
      ;;

    *[[?*]*)
      # pattern
      help "$1" | "${PAGER:-less}"
      ;;

    *)
      # something else, presumed to be an external command
      # or options for the man command or a section number
      #
      # in case no man page is found, try to run the command with the
      # --help option as a last resort
      command man "$@" 2> /dev/null || "$@" --help | "${PAGER:-less}"
      ;;
  esac
}
