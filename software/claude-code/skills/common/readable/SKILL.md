---
name: readable
description: Write an assistant reply again the way the user likes to read it - only what matters, lists in place of series, examples kept, within an exact word limit. Use for `/readable`, and when the user says a reply is too long, too dense or hard to read, or asks for a "tl;dr" or "the short version" of a reply.
argument-hint: "[how many replies back, 1 is the latest] [what to focus on]"
model: best
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/readable.py *)
---

# readable

Edit one reply that you gave in this session, and show the edited version as a new reply.
The original stays in the conversation. Use everything that the session tells you about
what the user wants: the edit is a selection by importance, not a trim.

Arguments: `$ARGUMENTS`

- A number selects the reply: `1` or no number is the latest reply, `2` is the one before it.
- All other text is the focus. Judge importance against the focus, and delete what does
  not serve it.

## Steps

1. Get the exact limit. `<n>` is the number from the arguments, or 1:

   ```
   ${CLAUDE_SKILL_DIR}/scripts/readable.py limit --reply <n>
   ```

   The script reads the reply from the session transcript and prints its first line, its
   word count and the word limit. If the first line is not the reply that you expect,
   write the correct reply to a file in the scratchpad and add `--original-file <path>`
   to both commands.

2. Write a draft. Apply the rules under "Concerns" below.

3. Check the draft:

   ```
   ${CLAUDE_SKILL_DIR}/scripts/readable.py check --reply <n> <<'READABLE_DRAFT'
   <the draft>
   READABLE_DRAFT
   ```

   If a hook blocks the heredoc, write the draft to a file in the scratchpad and use
   `--draft-file <path>`. If the script prints `NOT OK`, correct the draft and check it
   again. After three failed checks, show the best draft and say which check failed.

4. Reply with the draft only, and end it with the line that the script printed. Write no
   introduction, and do not say what you changed.

## Concerns

The reader's preferences are in the user's CLAUDE.md (`~/.claude/CLAUDE.md`), section
"Writing style for answers to me". It is already in your context. Apply all of it, and
especially these rules from "Content and structure":

- the importance order;
- the noise list;
- the rule for parallel items (a lead-in line, then one item on each line);
- the rule for examples (keep them, and shorten the explanation instead).

Do not copy those rules into this skill: one copy cannot drift from another. The rules
below are only for editing a reply that exists. The script has a check for a rule when a
script can check it.

- Select by importance; do not shorten each sentence a little.
- Keep each part that the user's request asked the reply to contain.
- Write the result as a short, complete message. Merge points that belong together.
- The word limit from the script is a hard limit. Fewer words is better when nothing
  important is lost.
- Keep an example that comes from the user's own words in those words. Delete an example
  only when a second example shows the same point.

## Rules for every edit

- Add no fact, guess or comment that the reply does not have.
- Keep every question to the reader.
- Keep each number, path, command and identifier exact.
- Keep each code block and table that you keep verbatim. They are not in the word count.
- If no rule changes the reply, say that in one line and do not repeat the reply.
