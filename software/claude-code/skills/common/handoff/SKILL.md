---
name: handoff
description: Write a handoff document so another person (or a fresh session) can pick up this work where it stands. Use when the user says they are handing off, passing this to a teammate, going on holiday/EOD and someone else continues, or asks for a handoff/handover summary. Captures the goal, decisions and their why, what was tried and rejected, current state of the branch, and what is left — then prints a paste-ready opening prompt for the person taking over.
---

# Handoff

Turn the current session into a self-contained document a teammate can act on, colocated with the work-in-progress branch it belongs to.

The reader is a competent engineer who was **not** in this session. They know the codebase; they do not know what you tried, what you rejected, or why. Everything that lived only in this conversation is exactly what you must write down.

## Write from the reader's position, not yours

You have the session history, the scratchpad, the working tree and this conversation. They have this document and whatever is genuinely shared with them. That asymmetry is the whole difficulty, and it produces three rules:

- **Never cite evidence the reader cannot reach.** A claim resting on a scratchpad file, an uncommitted path, a local branch, terminal scrollback, or "as we saw earlier" is unverifiable to them and therefore worthless. State the **finding** and that it was verified — not the local artifact it came from.
- **Never write "you will not receive X."** If something matters, make it reachable: embed it in the document, attach it to the tracking story, or ask the user to commit it. If it does not matter, leave it out. A list of things the reader is missing is an unfinished handoff, not a caveat.
- **Resolve local-only state rather than disclosing it.** Anything you are tempted to warn them about is a gap to close before the document is done.

The same test applies to the document's own location: if it lives at a path only this machine has, saying "read `<path>`" hands them nothing. Decide how it actually reaches them (committed, attached to the story, or pasted) and write the handover instruction to match.

## 1. Read the ground truth first

Never describe the branch from memory. Run these (in the repo root or the relevant worktree) and use the real output:

```bash
command git branch --show-current
command git status --short
command git log --oneline @{upstream}..HEAD 2>/dev/null || command git log --oneline -10
command git diff --stat HEAD
command git stash list
```

Note whether the branch has an upstream and whether local commits are unpushed — if they are, the teammate cannot see this work yet, and that goes in the handoff.

If the working tree is dirty, do not commit it on your own initiative — committing someone's unfinished source changes is their call. But do not simply warn about it either. For each uncommitted path, decide which it is:

- **Load-bearing for the next step** — the reader cannot proceed without it. Get it reachable: ask the user to commit it, or reproduce its content in the handoff. Say plainly that the work is blocked until that happens.
- **Not load-bearing** — omit it entirely. It is noise, and listing it invites the reader to hunt for something they do not need.

The same applies to unpushed commits: if the branch is unpushed the reader cannot see the work at all, so that is a blocking item in **What's left** with a named action, not a footnote.

If there is no git repo, skip the branch sections and say so — the document is still useful.

## 2. Reconstruct the session, honestly

Mine the conversation for what a diff cannot show:

- **The actual goal**, including how it shifted mid-session if it did.
- **Decisions and their why** — the reason a decision was made is the part that gets lost, and the part that stops the teammate re-litigating it.
- **Dead ends**: what was tried and abandoned, and what the failure looked like. This saves the most time of anything in the document. Do not quietly omit an approach because it didn't work — that omission is why it gets retried.
- **Verification state**: which tests/linters/type checks were actually run, and their real result. If something is failing or was never run, say so plainly. Never imply a green run you did not see.
- **Open questions** the user has not decided yet, and any question you were waiting on an answer for.
- **Gotchas** that cost this session time: env setup, credentials, a flaky suite, a slow command, a non-obvious invocation.
- **What's left**, ordered, with the first concrete next action named.

- **Throwaway scripts that are still useful.** Audit queries, verification probes, one-off reports written to a scratchpad or temp directory during the session usually die with it, even though the next person needs exactly them. Do not point at their paths. Instead:
  - **Embed the script in the handoff**, in a fenced block, when it is short enough not to bury the prose — roughly under a screen or two. A reader who can copy it whole needs nothing else.
  - **Attach it to the tracking story** when embedding would swamp the document, and say which story and which comment.
  - **Ask whether to commit it** to the repo when it has lasting value beyond this handoff (a reusable report, a migration verifier). Do not commit it unprompted.
  Whichever route, the handoff must contain what the script *does*, how to run it, and what a correct result looks like — so a reader can judge its output without reverse-engineering it.

Rules: no invention. If you don't know something, write `Unknown —` and what it would take to find out. No secrets, tokens, credentials, or personal data in the document — reference where they live (a secret manager, the env file) instead. Host names, account identifiers and connection details are fine only if they are already in the repo or the story; otherwise describe how to obtain them.

## 3. Write the file

Path: `.claude/handoffs/YYYY-MM-DD_<branch-or-topic>.md` under the project root (create the directory if needed). Use the current date; get it from `command date +%F`, not from assumption. Sanitize the branch name for the filename. If a handoff for this branch and date already exists, read it and update it rather than adding a near-duplicate.

Structure — keep it skimmable, prose over ceremony, cut any section that has nothing real in it:

```markdown
# Handoff: <short title of the work>

**Branch:** `<branch>` (`<pushed / N unpushed commits / no upstream>`)
**Story:** <id or none>
**Date:** <YYYY-MM-DD>

## Goal
What we set out to do and why it matters.

## Where it stands
Honest current state: what works, what is half-built, what is untouched.

## Decisions made
- **<decision>** — why, and what the alternative was.

## Tried and rejected
- **<approach>** — what happened, why it was abandoned.

## Branch state
Commits the reader can actually see, and whether they are pushed. Anything not yet reachable
belongs in **What's left** as an action, not here as a caveat.

## Scripts and queries you'll need
Embedded in full, or a pointer to the story comment holding them, plus what a correct
result looks like. Omit the section if there were none.

## Verification
What was run, and the actual result. What was not run.

## What's left
1. <first concrete next action>
2. …

## Gotchas
Things that will cost the next person an hour if nobody tells them.

## Open questions
Decisions still owned by the user or the team.
```

Reference files as `path/to/file.py:42` so they are clickable.

## 4. Hand it over

Print, in the chat, a **paste-ready opening prompt** for the teammate's fresh session — fenced, so they can copy it whole. It should name the branch, say where the handoff actually is **from the reader's side**, and state the first task. If the document is only on this machine, the prompt cannot send them to its path; either the user shares it first, or the prompt carries the essentials itself. For example:

```
I'm picking up work on branch `<branch>`. Read the handoff attached to <story> first — it
has the decisions, dead ends, and what's left. Then start on <first next action>.
```

Then tell the user the shortest list of things that make the handoff land, based on the real state you read: share the document by whatever route you agreed (commit, story attachment, paste), push the branch if it is unpushed, and resolve any load-bearing uncommitted work. **Ask before committing or pushing** — do not push a WIP branch or commit on the user's behalf unless they say so in this session. When they do approve, follow the repo's commit-message convention.

Finally, re-read your own document once as the reader: every claim checkable, no reference to anything only this machine has, and no "you will not receive" anywhere. Note anything you genuinely could not determine so the user can fill it in before sending.
