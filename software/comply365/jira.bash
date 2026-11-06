# The Jira site and project key are deliberately not in this public repo: they
# live in a per-machine file that nothing here writes (jira.rb warns while it is
# missing).
jira() {
  if [[ $# -ne 1 || ! "$1" =~ ^[0-9]+$ ]]; then
    >&2 echo 'Usage: jira 472'
    return 1
  fi

  local config="$HOME/.config/dotfiles/jira" prefix=''
  # Exit status ignored on purpose: `read` fails on a file with no trailing
  # newline even though it has already assigned the line.
  { read -r prefix < "$config"; } 2> /dev/null
  if [[ -z "$prefix" ]]; then
    >&2 echo "jira: $config must hold the story URL up to the number, e.g. https://<site>.atlassian.net/browse/<PROJECT>-"
    return 1
  fi

  browse "$prefix$1"
}
