export PAGER=less

export LESS="\
  --quit-if-one-screen \
  --raw-control-chars \
  --no-init \
  --IGNORE-CASE \
  --hilite-search \
  --jump-target=$(expr $(tput lines) / 2)\
"
