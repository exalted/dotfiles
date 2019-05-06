export PAGER=less

export LESS="\
  --quit-if-one-screen \
  --RAW-CONTROL-CHARS \
  --no-init \
  --IGNORE-CASE \
  --hilite-search \
  --jump-target=$(expr $(tput lines) / 2) \
"
