export PAGER=less

# `--jump-target` takes a fraction of the screen height, evaluated by less at
# runtime. It used to be $(expr $(tput lines) / 2), computed once here at shell
# startup: stale after any window resize, and worse — where TERM is unset (a
# GUI-spawned shell, cron) tput fails, expr fails, and LESS is left holding a
# valueless --jump-target=. less then refuses the whole variable with "Value is
# required after -j" and displays nothing at all.
export LESS="\
  --quit-if-one-screen \
  --QUIT-AT-EOF \
  --RAW-CONTROL-CHARS \
  --no-init \
  --IGNORE-CASE \
  --hilite-search \
  --jump-target=.5 \
"
