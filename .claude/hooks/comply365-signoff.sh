#!/usr/bin/env bash
# Record a human's verdict on a manual criterion from software/comply365/SPEC.md.
#
#   .claude/hooks/comply365-signoff.sh AC-14 pass
#   .claude/hooks/comply365-signoff.sh AC-23 fail
#
# The verdict is stored together with a digest of the files that criterion
# depends on, so it expires by itself when that code changes again — a sign-off
# is a statement about a specific state of the tree, not a permanent waiver.
set -euo pipefail

id="${1:?usage: comply365-signoff.sh <AC-id> pass|fail}"
verdict="${2:?usage: comply365-signoff.sh <AC-id> pass|fail}"
case "$verdict" in pass|fail) ;; *) echo "verdict must be pass or fail" >&2; exit 2 ;; esac

repo="$(git rev-parse --show-toplevel)"
cd "$repo"
SPEC=software/comply365/SPEC.md
LEDGER=.claude/comply365-manual-signoff.json

sed -n '/<!-- manual-checks/,/-->/p' "$SPEC" | command grep -qE "^${id}\|" \
  || { echo "$id is not a manual criterion in $SPEC" >&2; exit 2; }

# Must match comply365-spec-check.sh's batch_digest exactly, or a fresh sign-off
# would read as stale immediately. One digest for the whole batch on purpose: a
# change anywhere re-opens every manual criterion.
repo="$(git rev-parse --show-toplevel)"
digest="$(git -C "$repo" ls-files --cached --others --exclude-standard -- 'software/comply365/*.bashrc' 'software/comply365/*.rb' software/comply365/zshenv software/bash/prompt-command.bashrc software/bash/prompt.bashrc software/node/nvm-loader.sh software/node/bashrc software/homebrew/shellenv.sh software/homebrew/bashrc software/watch/bashrc software/git/bin/git-hist software/bash/pager.bashrc software/iterm2/bashrc profiles.rb 2>/dev/null \
    | command sort \
    | while read -r f; do command shasum -a 256 "$repo/$f"; done \
    | command shasum -a 256 | cut -c1-16)"

python3 - "$LEDGER" "$id" "$verdict" "$digest" <<'PY'
import json,sys,os,datetime
ledger,id,verdict,digest=sys.argv[1:5]
try: d=json.load(open(ledger))
except Exception: d={}
d[id]={"status":verdict,"digest":digest,"at":datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
os.makedirs(os.path.dirname(ledger),exist_ok=True)
json.dump(dict(sorted(d.items())),open(ledger,"w"),indent=2)
open(ledger,"a").write("\n")
print(f"{id}: {verdict} (digest {digest})")
PY
