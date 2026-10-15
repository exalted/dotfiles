#!/bin/sh
# Entry point of the com.dotfiles.comply365-recap launch agent: the weekday,
# unattended recap (skills/work/comply365-recap).
#
# launchd runs this script directly, by the absolute path the installer rendered
# into the plist, with a bare environment: no shell profile, no Homebrew on PATH.
# So this script finds the dotfiles checkout from its own real path and puts
# Homebrew (where `claude` and `uv` live) on PATH itself.

self="$(/usr/bin/readlink -f "$0")"
dotfiles="$(cd "$(/usr/bin/dirname "$self")/../.." && pwd)"
. "$dotfiles/software/homebrew/shellenv.sh"

log="$HOME/Library/Logs/recap.log"
/bin/mkdir -p "$(/usr/bin/dirname "$log")"
exec >>"$log" 2>&1

echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') start"

# launchd counts a DarkWake as a wake: with the lid closed, the Mac wakes for
# about two seconds every quarter hour, starts the job, and sleeps again. The run
# then crawls for hours, two seconds at a time, inside a closed Mac, maybe in a
# bag. Only a full wake has the Graphics capability. A sleeping Mac freezes this
# loop too, so the wait costs nothing.
fully_awake() {
  /usr/bin/pmset -g systemstate | /usr/bin/grep -q Graphics
}
if ! fully_awake; then
  echo "waiting for a full wake"
  until fully_awake; do /bin/sleep 60; done
  echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') fully awake"
fi

# A directory of its own, so the run loads no project's CLAUDE.md and its
# work files (work/<date>/) land outside every repo.
state="$HOME/.local/state/recap"
/bin/mkdir -p "$state"
cd "$state" || exit 1

scripts='~/.claude/skills/comply365-recap/scripts'
note="$HOME/.claude/skills/comply365-recap/scripts/note.py"

# Runs at 07:47, on wake after a missed 07:47, and at every login. prepare.py
# applies read ticks from catch-up notes, then says whether a recap is due, so
# only the first of those starts on a weekday ends up calling Claude.
prepared=0
uv run --quiet --no-project --script "$HOME/.claude/skills/comply365-recap/scripts/prepare.py" || prepared=$?
case "$prepared" in
  0) ;;
  3)
    echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') end: nothing due"
    exit 0
    ;;
  *)
    uv run --quiet --no-project --script "$note" \
      --error "The scheduled run could not start: prepare.py exited with $prepared. See ~/Library/Logs/recap.log"
    exit "$prepared"
    ;;
esac

# Only the plugin servers, never the claude.ai connectors: a connector with the
# same service replaces its plugin, and an unauthorized one leaves the run with no
# Jira tools. Headless runs also start before remote servers finish connecting,
# so the first turn waits for them.
export ENABLE_CLAUDEAI_MCP_SERVERS=false
export CLAUDE_CODE_MCP_STARTUP_WAIT_MS=60000

# Nobody is there to answer prompts: everything not pre-allowed here is denied.
# The skill reads GitLab, Jira and Slack and writes one Obsidian note through
# its own script; it never needs a write tool beyond its work files.
# The skill is hidden from the / menu (user-invocable: false), so the prompt
# names it and Claude starts it through the Skill tool. It runs on the most
# capable model, at the effort level meant for long, multi-step agent work:
# one run a day, so quality is worth more than its cost.
#
# caffeinate -i holds off idle sleep for this run only; it cannot keep a closed
# lid on battery awake, and should not. An awake run takes about ten minutes, so
# the alarm stops a hung one at 30 instead of leaving it to run on. SIGALRM
# survives the exec, and perl is the macOS stock way to get it: there is no timeout(1).
limit_minutes=30
# Nobody is there to pick up side tasks: keep the todo hooks silent (see skills/common/todo).
export CLAUDE_TODO_HOOKS=0
status=0
/usr/bin/caffeinate -i \
  /usr/bin/perl -e 'alarm shift; exec @ARGV or die "exec $ARGV[0]: $!\n"' "$((limit_minutes * 60))" \
  claude -p "Run the comply365-recap skill." \
  --model fable \
  --effort xhigh \
  --permission-mode acceptEdits \
  --permission-prompts none \
  --allowedTools "Skill,ToolSearch,Read,Write,\
Bash(uv run --quiet --no-project --script $scripts/*),\
Bash(trash *.local/state/recap/work/*),\
mcp__plugin_gitlab_gitlab__get_commit,\
mcp__plugin_atlassian_atlassian__getAccessibleAtlassianResources,\
mcp__plugin_atlassian_atlassian__searchJiraIssuesUsingJql,\
mcp__plugin_atlassian_atlassian__getJiraIssue,\
mcp__plugin_slack_slack__slack_read_channel,\
mcp__plugin_slack_slack__slack_read_thread,\
mcp__plugin_slack_slack__slack_search_public" \
  < /dev/null || status=$?

# The skill reports the failures it can name itself. This covers the ones it
# cannot: claude crashing, a sign-in it never reached, a run cut short.
if [ "$status" -eq 142 ]; then
  uv run --quiet --no-project --script "$note" \
    --error "The scheduled run stopped at its $limit_minutes-minute limit. See ~/Library/Logs/recap.log"
elif [ "$status" -ne 0 ]; then
  uv run --quiet --no-project --script "$note" \
    --error "The scheduled run stopped: claude exited with $status. See ~/Library/Logs/recap.log"
fi

echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') end exit=$status"
exit "$status"
