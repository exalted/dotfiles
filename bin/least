#!/usr/bin/env bash
# Don't run `most` if content is less than screen's height

# $(cat) is a shorthand for $(cat /dev/stdin)
# (Ref.: http://mockingeye.com/blog/2013/01/22/reading-everything-stdin-in-a-bash-script/)
CONTENT=$(cat)

FOLDED_CONTENT=$(fold -w $(tput cols) <<<"$CONTENT")

if (( $(wc -l <<<"$FOLDED_CONTENT") < $(tput lines) )); then
    echo "$CONTENT"; exit
fi

most <<<"$CONTENT"
