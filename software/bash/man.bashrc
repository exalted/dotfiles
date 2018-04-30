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
            command man "$@"
            ;;
    esac
}
