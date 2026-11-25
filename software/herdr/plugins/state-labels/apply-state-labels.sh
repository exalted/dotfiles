#!/bin/sh
# Herdr keeps state labels per pane and has no setting for all panes. Each run
# therefore reports the labels to every agent pane; a repeated report changes nothing.
set -u

herdr=${HERDR_BIN_PATH:-herdr}

# The list is captured first so that a failed listing fails the run, instead of
# looking like a session with no agents.
agents=$("$herdr" agent list) || exit 1
panes=$(printf '%s' "$agents" | jq -r '.result.agents[].pane_id') || exit 1

status=0
for pane in $panes; do
  "$herdr" pane report-metadata "$pane" \
    --source dotfiles.state-labels \
    --state-label 'blocked=🙋 Needs you' \
    --state-label 'working=⏳ Working' \
    --state-label 'done=📬 Unread' \
    --state-label 'idle=✅ Read' \
    --state-label 'unknown=🤔 Not sure' || status=1
done

exit "$status"
