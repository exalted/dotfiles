export PAGER=less

export LESS="\
  --quit-if-one-screen \
  --QUIT-AT-EOF \
  --RAW-CONTROL-CHARS \
  --no-init \
  --IGNORE-CASE \
  --hilite-search \
  --jump-target=$(expr $(tput lines) / 2) \
"
