---
name: sync-gitlab-repos
description: Bring the local GitLab checkouts under ~/Developer level with origin using fast-forward only, skipping any repo with ongoing work. Use when the user asks to update, sync, pull, refresh, or catch up their repos / local checkouts / the cwd's from GitLab, or asks for this before starting other work. Accepts an optional root path argument (default ~/Developer).
model: haiku
---

# Sync GitLab repos

Fast-forward every GitLab repo directly under the root (default `~/Developer`, or the path given as argument) that is simply behind `origin` and has no ongoing work. Never create merge commits, never rebase, never rewrite history, never push.

Run this to completion before any other work the user asked for in the same message.

This skill is user-scoped and works from any working directory: `~/Developer`, a project inside it such as `~/Developer/cortex`, or anywhere else. Do not `cd`. The script resolves the root itself and every git call uses `git -C`. When the session's own project is one of the repos, it gets no special treatment: the same rules decide whether it is updated or skipped.

## 1. Inspect

Run the bundled script and read its full output:

```bash
bash ~/.claude/skills/sync-gitlab-repos/scripts/inspect.sh [root]
```

Pass a root only when the user names one; otherwise omit it and the script uses `~/Developer`. It fetches with `--all --prune` and prints, per repo: remote check, branch and upstream, behind/ahead counts, stash count, in-progress operation, modified/staged files, untracked files, and (when `.gitignore` is modified) its diff plus incoming commits touching `.gitignore` or `.claude/`.

Repos whose `origin` is not on gitlab.com are printed as SKIP (e.g. `dotfiles` on GitHub). Never touch them.

**If the script exits 2 with `FETCH FAILED` lines, stop.** The behind/ahead numbers are stale and must not be acted on. The usual cause is an expired GitLab SAML SSO session: the fetch output contains a `https://gitlab.com/groups/<group>/-/saml/sso?token=...` URL. Tell the user to open that URL in the browser and sign in (they can run `! open '<url>'` in the prompt), then re-run the script from step 1. Do not try alternative auth paths or work around the failure.

## 2. Classify each GitLab repo

| Condition | Action |
|---|---|
| `behind: 0` | Already up to date. Nothing to do. |
| `ahead > 0`, or an op in progress, or no upstream | Skip. Report why. Never push, never resolve. |
| Modified or staged tracked files other than the `.gitignore` exemption below | Skip as ongoing work. Report the dirty files. |
| Only untracked files (plans, scripts, jsonc dumps under `.claude/`, etc.) | Not ongoing work. Update. |
| Clean, behind, not ahead | Update. |
| Only dirty file is `.gitignore` and the diff solely comments out or removes the `.claude` ignore rule (`/.claude/`, `.claude`) | Exemption. Update with stash/pop (step 3b), but only if no incoming commit touches `.gitignore` or `.claude/`. Otherwise skip and report. |

A pre-existing stash entry is not by itself a reason to skip, but the count must be unchanged afterwards.

## 3. Update

**3a. Clean repos:**

```bash
command git -C "$d" merge --ff-only @{u}
```

**3b. `.gitignore`-exempt repos:**

```bash
command git -C "$d" stash push -m "sync-gitlab-repos: temp stash .gitignore" -- .gitignore
command git -C "$d" merge --ff-only @{u}
command git -C "$d" stash pop
```

If `stash pop` conflicts, stop and tell the user. Do not resolve it yourself and do not drop the stash.

## 4. Verify and report

Re-check every GitLab repo: `status -sb` first line, stash count, dirty file count. Confirm stash counts match the pre-update numbers and that pre-existing dirty state is back in place.

Then print the report in exactly this shape. One row per repo, sorted: updated repos first by commits pulled descending, then up-to-date, then skipped, then non-GitLab. Keep the reason column short; details go below the table.

```
🔄 GitLab repo sync · <root> · <N> repos

| Status | Repo | Result | Note |
|---|---|---|---|
| ⬇️ updated | `cortex` | 47 commits | untracked files left alone |
| ⬇️ updated | `web-cockpit` | 8 commits | `.gitignore` stashed → ff → popped |
| ✅ was up-to-date | `repo-a` | nothing to pull | |
| ⏸️ on hold | `web-safety` | behind 3 | modified tracked files |
| ⛔ blocked | `repo-b` | ahead 2 | local commits not on origin |
| 🚫 not GitLab | `dotfiles` | untouched | github.com/exalted/dotfiles |

📊 7 updated · 2 up to date · 1 skipped · 1 non-GitLab
🧹 0 stash entries everywhere · pre-existing dirty state restored
```

Every Status cell is the icon followed by its term, both fixed and written exactly as below. Because the term names the category, Result holds only the specifics such as counts:

- ⬇️ updated: fast-forwarded this run
- ✅ was up-to-date: already level with origin, nothing pulled
- ⏸️ on hold: skipped for ongoing work or a stash conflict
- ⛔ blocked: skipped because the branch is ahead, has no upstream, or has an op in progress
- 🚫 not GitLab: origin is not a GitLab remote, never touched
- ❌ fetch failed: report only, then exit early per step 1

Omit the 🧹 line's second clause when nothing was stashed. If any repo was skipped, follow the table with one bullet per skipped repo listing the concrete dirty files or the blocking condition, then a single closing line offering, but not performing, to stash and fast-forward it.

Do not add a headline sentence before the report or a recap after it.

## Hard rules

- `merge --ff-only` is the only way a branch moves. No `pull` without `--ff-only`, no `rebase`, no `reset`.
- Never push, never commit, never drop or apply a stash you did not create in this run.
- Stash only `.gitignore` and only under the exemption above. Never stash real work without an explicit go-ahead.
- Prefix built-in commands with `command` per the user's global instructions.
