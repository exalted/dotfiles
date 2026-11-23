_claude_starts_session() {
  [[ $- == *i* && -t 0 && -t 1 ]] || return 1

  case "${1:-}" in
    agents|attach|auth|auto-mode|daemon|doctor|gateway|import|install|logs|mcp|plugin|purge|remote-control|respawn|rm|self-hosted-runner|setup-token|stop|ultrareview|update) return 1 ;;
  esac

  local arg
  for arg in "$@"; do
    case "$arg" in
      -p|--print|-h|--help|-v|--version) return 1 ;;
    esac
  done
}

_claude_asks_for_name() {
  _claude_starts_session "$@" || return 1

  local arg
  for arg in "$@"; do
    case "$arg" in
      -n|--name|-r|--resume|-c|--continue|--session-id|--from-pr) return 1 ;;
    esac
  done
}

# Mirrors what Claude Code does to a name (control and invisible characters
# become spaces, 200 characters at most) and also drops a leading "-" so that
# `-n` cannot read the name as a flag.
_claude_clean_session_name() {
  printf '%s' "$1" | perl -CSDA -pe '
    s/[\p{Cc}\p{Cf}\p{Zl}\p{Zp}]/ /g;
    s/\s+/ /g;
    s/^[\s-]+//;
    $_ = substr($_, 0, 200);
    s/\s+$//;
  '
}

# Prints the cleaned text when it can serve as (part of) a name: one line, short,
# no markup, no URL, at least one letter or digit. Wide characters (CJK, emoji)
# are refused because the menu counts characters, not terminal columns.
_claude_eligible_entry() {
  local raw=$1 name
  (( ${#raw} <= 200 )) || return 1
  raw=${raw#"${raw%%[![:space:]]*}"}
  raw=${raw%"${raw##*[![:space:]]}"}
  [[ $raw != *$'\n'* && $raw != *$'\r'* ]] || return 1

  name=$(_claude_clean_session_name "$raw")
  (( ${#name} <= 60 )) || return 1
  [[ $name == *[[:alnum:]]* ]] || return 1
  [[ $name != *[\<\>\{\}]* && $name != *://* ]] || return 1
  printf '%s' "$name" | perl -CSDA -ne 'exit(/[\p{East_Asian_Width=W}\p{East_Asian_Width=F}]/ ? 1 : 0)' || return 1

  printf '%s' "$name"
}

_claude_warn() {
  printf 'claude wrapper: Clipy history unavailable, using the clipboard only: %s\n' "$1" >&2
}

# Fills _claude_entries with up to three names, newest first. Clipy's history
# supplies them only while its newest row is the clipboard now; any mismatch
# (Clipy not running, an excluded app, a changed database) leaves just the
# clipboard, so a stale history entry is never offered.
_claude_clipboard_entries() {
  _claude_entries=()
  command -v pbpaste >/dev/null || return 1

  local current first
  current=$(pbpaste | command head -c 201)
  first=$(_claude_eligible_entry "$current") || return 1
  _claude_entries=("$first")

  local database="$HOME/Library/Application Support/com.clipy-app.Clipy/sqlite.db"
  [[ -e $database ]] || return 0
  if ! command -v sqlite3 >/dev/null; then
    _claude_warn 'sqlite3 not found'
    return 0
  fi

  local output
  if ! output=$(sqlite3 -readonly "$database" "
    SELECT CASE WHEN length(text) > 200 OR instr(text, char(10)) > 0 OR instr(text, char(13)) > 0
                THEN '' ELSE text END
    FROM (SELECT trim(title, ' ' || char(9) || char(10) || char(13)) AS text, updateAt
          FROM pasteboardHistories)
    ORDER BY updateAt DESC LIMIT 3" 2>&1); then
    _claude_warn "cannot read the history (${output%%$'\n'*})"
    return 0
  fi

  local -a rows
  mapfile -t rows <<< "$output"

  local entry
  entry=$(_claude_eligible_entry "${rows[0]:-}") && [[ $entry == "$first" ]] || return 0

  _claude_entries=()
  local row existing duplicate
  for row in "${rows[@]}"; do
    entry=$(_claude_eligible_entry "$row") || break
    duplicate=0
    for existing in "${_claude_entries[@]}"; do
      [[ $existing == "$entry" ]] && duplicate=1
    done
    (( duplicate )) || _claude_entries+=("$entry")
  done
}

# Prints the typed line; returns 1 when the user goes back with Esc or Ctrl+D.
# The bindings live in a subshell, so they never leak into the user's shell.
_claude_read_name() {
  (
    bind '"\e": "\C-u\C-d"'
    bind 'set keyseq-timeout 50'
    bind 'set bell-style none'
    read -r -e -i "${2:-}" -p "$1" line && printf '%s' "$line"
  )
}

# `_claude_ask_name <prompt> [prefill]`. Asks again on an empty answer, so
# leaving the prompt takes Esc or Ctrl+D. Sets _claude_typed; returns 1 when the
# user leaves.
_claude_ask_name() {
  local line prefill=${2:-}
  while true; do
    line=$(_claude_read_name "$1" "$prefill") || { printf '\e[1A\r\e[2K'; return 1; }
    line=$(_claude_clean_session_name "$line")
    if [[ -n $line ]]; then
      _claude_typed=$line
      return 0
    fi
    prefill=''
    printf '\e[1A\r\e[2K'
  done
}

_claude_shorten() {
  local max=$(( ${COLUMNS:-80} - 20 ))
  (( max >= 10 )) || max=10
  if (( ${#1} > max )); then
    printf '%s…' "${1:0:max-1}"
  else
    printf '%s' "$1"
  fi
}

# The menu needs 40 columns (its hint lines shrink to fit) and enough rows, and
# a terminal that redraws.
_claude_menu_fits() {
  [[ -n ${TERM:-} && $TERM != dumb ]] || return 1
  (( ${COLUMNS:-80} >= 40 && ${LINES:-24} >= ${#_claude_entries[@]} + 9 ))
}

# One menu for everything. Rows: "Type something…" and one per clipboard entry.
# Digits combine entries in pick order, any other printable key starts typing.
# Sets _claude_typed and returns 0 when a name was chosen; returns 1 to skip.
_claude_choose_name() {
  local count=${#_claude_entries[@]} height=$(( ${#_claude_entries[@]} + 6 ))
  # One entry has nothing to combine: it becomes the top row, without a number.
  local single=0 type_row=0
  (( count == 1 )) && single=1 type_row=1
  local -a picked=() kept
  local cursor=0 key next sequence code joined='' prefill index found

  _claude_choose_joined() {
    joined=''
    for index in "${picked[@]}"; do
      joined+="${joined:+ }${_claude_entries[index]}"
    done
  }

  _claude_choose_draw() {
    local row text marker range hint
    local columns=${COLUMNS:-80}
    _claude_choose_joined
    printf '\r\e[2K%s\n\r\e[2K\n' 'Session name'
    for (( row = 0; row <= count; row++ )); do
      if (( row == type_row )); then
        text='Type something…'
      elif (( single )); then
        text=$(_claude_shorten "${_claude_entries[0]}")
      else
        text="$row  $(_claude_shorten "${_claude_entries[row - 1]}")"
      fi
      marker=' '
      if (( row > 0 )) && [[ " ${picked[*]} " == *" $(( row - 1 )) "* ]]; then
        marker='✔'
      elif (( row == cursor && ${#picked[@]} == 0 )); then
        marker='❯'
      fi
      if (( row == cursor && ${#picked[@]} == 0 )); then
        printf '\r\e[2K\e[36m  %s %s\e[0m\n' "$marker" "$text"
      else
        printf '\r\e[2K  %s %s\n' "$marker" "$text"
      fi
    done
    printf '\r\e[2K\n'
    if [[ -n $joined ]]; then
      printf '\r\e[2KName: %s\n' "$(_claude_shorten "$joined")"
      hint='Enter accept · Tab edit · ⌫ undo · Esc clear'
      (( columns >= 46 )) || hint='Enter ok · Tab edit · ⌫ · Esc clear'
    else
      printf '\r\e[2K\n'
      if (( single )); then
        hint='Type to name it · ↑↓ Enter choose · Tab edit · Esc skip'
        (( columns >= 60 )) || hint='↑↓ Enter choose · Tab edit · Esc skip'
      else
        range="1-$count"
        hint="Type to name it · ↑↓ Enter choose · $range combine · Esc skip"
        (( columns >= 60 )) || hint="↑↓ Enter · $range combine · Esc skip"
      fi
    fi
    printf '\r\e[2K%s\n' "$hint"
  }

  _claude_choose_erase() {
    printf '\e[%dA\e[J' $height
  }

  # Returns 0 with _claude_typed set, or 1 when the user went back (menu redrawn).
  _claude_choose_prompt() {
    _claude_choose_erase
    _claude_ask_name 'Session name (Esc/Ctrl+D to go back): ' "$1" && return 0
    _claude_choose_draw
    return 1
  }

  _claude_choose_accept() {
    _claude_choose_erase
    _claude_typed=$1
    printf 'Session name: %s\n' "$_claude_typed"
  }

  _claude_choose_draw
  while true; do
    IFS= read -rsn1 key || { _claude_choose_erase; return 1; }

    if [[ $key == $'\e' ]]; then
      if IFS= read -rsn1 -t 0.05 next; then
        sequence=$next
        if [[ $next == '[' || $next == O ]]; then
          while IFS= read -rsn1 -t 0.05 next; do
            sequence+=$next
            code=$(LC_ALL=C printf '%d' "'$next")
            (( code >= 64 && code <= 126 )) && break
          done
        fi
        key=$'\e'$sequence
      fi
    fi

    case $key in
      $'\e[A')
        (( ${#picked[@]} )) || cursor=$(( (cursor + count) % (count + 1) ))
        ;;
      $'\e[B')
        (( ${#picked[@]} )) || cursor=$(( (cursor + 1) % (count + 1) ))
        ;;
      $'\e')
        if (( ${#picked[@]} )); then
          picked=()
        else
          _claude_choose_erase
          return 1
        fi
        ;;
      $'\e'*) continue ;;
      $'\x04')
        _claude_choose_erase
        return 1
        ;;
      '')
        if (( ${#picked[@]} )); then
          _claude_choose_joined
          _claude_choose_accept "$(_claude_clean_session_name "$joined")"
          return 0
        elif (( cursor != type_row )); then
          _claude_choose_accept "${_claude_entries[single ? 0 : cursor - 1]}"
          return 0
        fi
        _claude_choose_prompt '' && return 0
        continue
        ;;
      $'\t')
        prefill=''
        if (( ${#picked[@]} )); then
          _claude_choose_joined
          prefill=$joined
        elif (( cursor != type_row )); then
          prefill=${_claude_entries[single ? 0 : cursor - 1]}
        fi
        _claude_choose_prompt "$prefill" && return 0
        continue
        ;;
      $'\x7f'|$'\b')
        (( ${#picked[@]} )) && unset 'picked[${#picked[@]}-1]'
        ;;
      [1-9])
        if (( single && key == 1 )); then
          cursor=0
        elif (( ! single && key <= count )); then
          index=$(( key - 1 ))
          found=0 kept=()
          for next in "${picked[@]}"; do
            if (( next == index )); then found=1; else kept+=("$next"); fi
          done
          if (( found )); then picked=("${kept[@]}"); else picked+=("$index"); fi
        else
          _claude_choose_prompt "$key" && return 0
          continue
        fi
        ;;
      *)
        if [[ $key == [[:print:]] && $key != ' ' ]]; then
          _claude_choose_prompt "$key" && return 0
        fi
        continue
        ;;
    esac
    printf '\e[%dA' $height
    _claude_choose_draw
  done
}

claude() {
  local -a args=()
  local arg skip_name=0
  for arg in "$@"; do
    if [[ $arg == --no-name ]]; then
      skip_name=1
    else
      args+=("$arg")
    fi
  done

  _claude_starts_session "${args[@]}" && upgrade-cask-daily claude-code@latest

  if (( skip_name )) || ! _claude_asks_for_name "${args[@]}"; then
    command claude "${args[@]}"
    return
  fi

  local name=''
  if _claude_clipboard_entries && _claude_menu_fits; then
    _claude_choose_name && name=$_claude_typed
  elif _claude_ask_name 'Session name (Esc/Ctrl+D to skip): '; then
    name=$_claude_typed
  fi

  if [[ -n $name ]]; then
    command claude -n "$name" "${args[@]}"
  else
    command claude "${args[@]}"
  fi
}
