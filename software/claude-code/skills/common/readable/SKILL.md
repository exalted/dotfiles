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

2. Write a draft. Apply each concern below.

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

Each concern is one preference of the reader. The script has a check for a concern when a
script can check it.

### Keep what matters

Do not shorten each sentence a little. Decide what matters, keep that, and delete the rest.

- Find what the reader must know or must do. In order of importance:
  1. a question or a decision that waits for the reader;
  2. a result or an answer;
  3. a failure, a risk or a warning;
  4. an action that the reader must take;
  5. a fact that changes what the reader does next (a number, a path, a command, a name).
- Keep those. Put the most important one first.
- Keep each part that the user's request asked the reply to contain.
- Delete the noise: how the work was done, a restatement of the request that the user did
  not ask for, hedges, repeated points, courtesies, background that the reader has,
  options that were rejected, and details that change nothing for the reader.
- Write the result as a short, complete message. Merge points that belong together.
- The word limit from the script is a hard limit. Fewer words is better when nothing
  important is lost.

### Lists, not series

When a sentence holds two or more parallel items or steps (parts joined by commas,
semicolons, "and", "then"), write a short lead-in line and put each item on its own line.

- Use a numbered list when the order matters (steps, a sequence, a ranking), and bullets
  when it does not.
- Put one idea in each sentence and in each list item.

### Keep examples

An example is never noise. The reader often understands an example faster than the
explanation beside it.

- Keep each example that the reply gives: a sample value, an input and its result, a
  before and after, a concrete case.
- Keep an example that comes from the user's own words in those words.
- When the word limit is tight, shorten or delete the explanation, not the example.
- Delete an example only when a second example shows the same point.

## Rules for every edit

- Add no fact, guess or comment that the reply does not have.
- Keep every question to the reader.
- Keep each number, path, command and identifier exact.
- Keep each code block and table that you keep verbatim. They are not in the word count.
- If no concern changes the reply, say that in one line and do not repeat the reply.
