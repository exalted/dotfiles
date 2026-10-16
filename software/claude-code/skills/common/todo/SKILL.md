---
name: todo
description: Side tasks for the body of work in progress, and ideas for the project. Use for `/todo`, and whenever the user says things like "remind me later to X", "also do Y after this", "note that as an idea", "one day we should Z", asks "anything else we should be doing?", "any open questions?", "what is not settled yet?", or wraps up with "that's it for today". Also use it on your own, without being asked, the moment a reply defers work ("next week", "after the release", "once X answers"), work is blocked or handed to someone, you list follow-ups for the user, a decision or question is left open, or the user is about to stop; a plan file or handoff note does not replace recording it. A judge classifies each item as do-now, session task, or idea, and the user decides when the judge disagrees with them. Never records anything outside a git repository.
argument-hint: "[<text> | idea <text> | done|drop <n> | all | wrap-up]"
---

# todo

Side tasks live in one file per project, `<main worktree>/.claude/scratchpad.local/todos.md`,
grouped by body of work. Ideas live in the user's Obsidian note, one section per project.
One script owns both files:

```
~/.claude/skills/todo/scripts/todo.py --session <id> <subcommand> …
```

The session id is `$CLAUDE_CODE_SESSION_ID` in your Bash environment; the SessionStart
context also names it. Pass `--session` explicitly when the variable is unset. Outside a
git repository the script refuses; say so and record nothing.

## Judge first

Every item, from `/todo <text>`, from plain words, or from your own observation, is
classified before anything is written. Say the route in one line, then act.

| Route | When | Then |
|---|---|---|
| Do now | Small, inside the current request's files and scope, no change of plan. | `add --by …`, do it, report, `list` then `remove <n>`, return to the work in progress. |
| Session task | Belongs to the body of work in progress and fits this session, but not now. | `add`. Offer it at the next resolution. |
| Idea | Unrelated, bigger scope, needs its own session, "one day" wording, or waits weeks on an event outside the session (a release, a month of production data). | Condense to 1 to 3 sentences that will remind the user what it was about. For a follow-up that waits on an event, also name the trigger, what to look at and what it should tell, so it can be acted on cold. Show them. On a yes, or a reworded yes, run `idea --text "…"`. |

Hint words steer the judge: "idea", "one day" lean idea; "now", "while you are in there"
lean do now; "after this", "before we push" lean session task. When the judge disagrees
with the user's wording, say why in one line and ask. The user decides.

`/todo idea <text>` and `/idea <text>` skip the judge: condense, show, write on a yes.

## Add

```
todo.py add --by user|claude --text "<task>" --while "<what the session was doing>" [--section <work-name>] [--story <KEY-1>] [--title "<session title>"]
```

- `--while` is one line a stranger session can relate to: "while fixing the nvm hook in
  prompt.bashrc".
- On the default branch the script needs `--section`. Use the scratchpad work-name of
  this body of work if the session has one, else `<STORY-ID>-<description>`, else
  `YYYY-MM-DD_<description>`. On any other branch the script derives it from the branch.
- `--story` only when the branch name does not carry the Jira key and the conversation does.
- `--title` when the session has a custom title.

## Your own tasks

You add tasks for yourself, with one line of notice ("Noted a task for later: …") and no
confirmation. Threshold: a unit of work with a purpose, a start and an end, that outlives
the current request. Ask both: would the user want to see this in a listing tomorrow, and
would it be lost if the session ended now? Both yes, or no line. A plan file, handoff note,
ticket comment or chat message does not count as kept: none of them is listed when the next
session starts.

Check at these moments, and record in the same turn: a reply of yours says "later", "next
week", "after the release" or "once X answers"; work is blocked or handed to someone; you
list follow-ups or open questions for the user; the user signals they are about to stop.

Never record cleanup of any kind: trashing scratchpad or temporary files, keeping,
committing or removing plan files, restoring local data, stopping local services. Each is
done, or dropped, when the work it belongs to ends.

| Add | Do not add |
|---|---|
| "Update the README once the flag name is confirmed" | "Edit prompt.bashrc", "run the tests", "report back" |
| "Decide: keep or drop the per-prompt PS1 rebuild, user has not answered" | "Ask the user about PS1" while the question is on screen |
| "Re-run the manual criteria after the shell change" | one line per criterion |
| "After the review, adjust the branch and merge it" | "Trash the scratchpad after the merge", "Decide whether to commit the plan file" |

Record a decision you deferred or a question the user did not answer as soon as it
arises, as `by claude`. Remove your own lines when done, without asking. Remove a user's
line only after doing the task and reporting it, or on the user's word. The judge applies
to your items too; an idea is proposed and written only on a yes, because the note is the
user's.

## List and close

- `/todo`: `list`. The current section in full, numbered, then the other open sections as
  one line each. `/todo all`: `list --all`.
- `/todo done 2`, `drop`, `cancel`, `delete`, `remove`, "scrap number 2", any such word:
  `remove 2`. Numbers are from the last `list` in this session; the script rejects a
  stale number and prints a fresh listing. Closing deletes the line; there is no history.

## At resolution

When the user's current request is resolved, verified and reported, or blocked on the
user, and before you stop: list the open tasks of the current section and ask which to
pick up. Do not start one on your own. The SessionStart and Stop hooks keep the list in
your context; between their notes, offer from memory.

## On a review question

"Anything else we should be doing?", "any open questions?", "what is not settled yet?":
run `list`, then answer in three groups: work to do, questions the user has not answered,
decisions still open. Re-read the conversation for anything you failed to record, record
it, then answer. Close nothing.

## At wrap-up

"That's it for today", "let's stop here", `/todo wrap-up`, or the body of work is
finished: run the review, then for each open task of the current section ask: done now,
drop, make it an idea, or keep for a later session. Keep is the exception; say so once if
the user keeps more than one. Done and dropped lines are removed; an idea goes through
the idea route.

## Next session

The SessionStart hook injects every open section with its context, and the last
session's open count when it ended with tasks. Judge which sections belong to the
current branch and work; mention the others in one line. Ask which to pick up, drop, or
turn into ideas.

## Setup

- Ideas need `~/.config/dotfiles/todo/ideas-note`: the absolute path of the note inside
  an Obsidian vault. See `ideas-note.example` next to this file. Without it, the idea
  route stops with a message naming the file; tasks work without it.
- Headless jobs set `CLAUDE_TODO_HOOKS=0` so the hooks stay silent.
- Tests: `/usr/bin/python3 -m unittest <this directory>/scripts/test_todo.py`.
