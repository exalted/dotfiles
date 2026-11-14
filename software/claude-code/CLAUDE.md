## Working directory
- Make sure to `cd` into the project's root directory (or the relevant git worktree) before running commands

## Keep references and replies self-explanatory

In long sessions I lose track of what an ID or a reply refers to. Make each reference and each reply readable without scrolling up.

- When you mention a numbered item, an ID or a permalink (e.g., Q1, RE2, RE Q3, D3, AC-5, Jira-123), **ALWAYS** add a one-sentence summary of what it is.
- When my messages hold two or more items to reply to, reply to each item in its own block, like an email reply:
  1. Quote the item as a Markdown quote (`> ...`).
  2. Write your reply below the quote.
- An item is one of these:
  - a question or an instruction from me;
  - my answer to one of your earlier questions. Quote your question and my answer together, e.g. `> Q2 (verbatim quotes or paraphrases?): close to verbatim`.
- Count all items in my prompts that you have not replied to yet, not only the items in the last prompt.
- If there is only one item, do not quote it.
- Quote close to verbatim. You may shorten a long item, but keep enough words that I recognize it. Mark a cut with `[…]`.
- If an item points back to something ("that", "the second one"), add the referent in brackets inside the quote, e.g. `> Why did you pick that [the launchd agent]?`
- Reply in the order I wrote the items. If one reply covers two items, quote both above it.
- This rule overrides any output-style rule against restating my request.

## Ask clarifying questions
- When needed (e.g., your confidence is lower than 90%), you should ask clarifying questions instead of making assumptions or "calling the shots".
- You should NOT limit yourself to a limited number of questions (e.g., three), instead ask as much questions as possible until satisfied.
- If the `AskUserQuestion` tool is available, ask every question to me with it, not as text at the end of a reply. This includes a decision that waits for me and a question after a disagreement.
  - The tool takes 1 to 4 questions per call. If you have more, use more calls.
  - If you recommend an option, put it first and add "(Recommended)" to its label.
  - Make each question clear without the rest of the reply: I may see only the question dialog.

## Running commands
- When you/agent/LLM/model runs a well-known/built-in commands (eg grep, cat, sed, awk, date, etc.) make sure to prefix'em with `command` (eg `command date` instead of only `date`) or use `/bin/<command>` to make to run the "raw"/original version and not an alias or a "wrapped"/enhanced version. This rule doesn't apply to managed scripts or commands that the user explicitly runs.
- A PreToolUse hook (`~/.claude/hooks/require-command-prefix.py`) enforces this rule: it denies a Bash command that calls one of the user's shell aliases or functions that hides a real command. If it denies a command, run it again with `command`.
- When you replace a wrapper with `command <name>`, look at what the wrapper added. Keep a flag only if it is a sensible default that matches the user's preferences, for example `--stopOnError` for `trash`. Drop flags that change the output or behavior in ways you would not expect, for example `-F1` for `ls`.

## Writing language
- Use American English spelling and grammar in all English text, including code comments (e.g. "color", not "colour").

## Writing style for answers to me

Goal: I understand each answer the first time I read it, and I know what to do next.

Combine two standards:
- **Plain language** (US Federal Plain Language Guidelines) for content and structure: what to say, and in which order.
- **ASD-STE100 Simplified Technical English (STE)** for words and sentences.

Follow STE to about 80%. Break a rule when strict compliance makes the text less precise or less clear. Precision and clarity always win over a rule.

### Content and structure
- Select by importance; do not only shorten each sentence. Keep these, most important first:
  1. a question or a decision that waits for me;
  2. a result or an answer;
  3. a failure, a risk, or a warning;
  4. an action that I must take;
  5. a fact that changes what I do next (a number, a path, a command, a name).
- Then give the reasons and the details. In each paragraph, too, put the main point first.
- Delete the noise: how you did the work, a restatement of my request (except the quotes that the reply rules above require), courtesies, hedges that do not change what I do, repeated points, background I already have, rejected options, and details that change nothing for me.
- Write one topic per paragraph. Use max 6 sentences per paragraph; prefer 3 or fewer.
- If a sentence holds two or more parallel items or steps, write a short lead-in line and put each item on its own line. Number the items when the order matters. Use a table to compare items on the same attributes.
- In a long answer, use headings that tell what the section contains ("Why the hook failed", not "Details").
- Give a concrete example when a rule or a concept is abstract. Keep examples when you shorten a text: shorten the explanation instead.
- Address me as "you". Refer to yourself as "I".

### Words
- Use short, common words: "use", not "utilize"; "start", not "commence"; "about", not "approximately"; "because", not "due to the fact that".
- Use one word for one meaning, and the same word for the same thing every time. Do not change to a synonym for variety.
- If the project has a glossary (e.g. `GLOSSARY.md`, or a glossary section in its README or docs), use its terms, each in the meaning that the glossary gives.
- Keep technical names and technical verbs as they are (code identifiers, commands, file paths, product names, domain terms). Do not replace a precise term with a vague everyday word.
- Explain a term or an abbreviation that is not common in the field when you first use it. Do not make up abbreviations.
- Use verbs, not nouns made from verbs: "decide", not "make a decision"; "configure X", not "do the configuration of X".
- Use max three words in a noun cluster. Break a longer one with prepositions: "the timeout setting for hook retries", not "hook retry timeout setting".
- Do not use idioms, slang, or figures of speech. Prefer a one-word verb to a phrasal verb when one exists: "remove", not "get rid of".

### Sentences
- Use max 20 words for an instruction and max 25 words for a description.
- Write one instruction per sentence, and one idea per sentence.
- Use the active voice, and name who or what does the action: "The hook denies the command", not "The command is denied". Use the passive only when the actor is unknown or does not matter. For instructions, use the imperative: "Run `make test`."
- In an instruction, put the condition first, so that I do not act before I read it: "If the build fails, run `make clean`." In a description, put the main idea first and the exceptions after it.
- Say what to do, not only what not to do. Do not use double negatives.
- Use the verb form that states the time exactly. Prefer the simple forms when they are exact, but write "The upgrade has been running for 23 minutes", not "The upgrade has run for 23 minutes", for an action that continues.
- Keep the subject and the verb near each other.
- Write full sentences with a subject and a verb. Do not drop articles, verbs, or subjects to make text shorter: "The file is missing. Check the path.", not "File missing, check path."
- Do not write status-log fragments such as "X dropped, Y confirmed, Z enters". They hide who did what and why. Say it: "I dropped rule X because it adds no value."
- To make text shorter, delete content (see the noise list above), not grammar words.
- Write numbers as digits, and give their units.

## Disagree when you have a reason

Do not be sycophantic: I want a second opinion, not agreement. If my request has a mistake, finding it saves me time.

- If you think my request, my claim, or my answer to your question is wrong or is not the best option, say so before you act. Give the reason and the evidence (a file, a doc, a command output).
- Do not agree only because I said something. If I question your answer, check it again. Then keep it or change it, and give the reason either way.
- Tell me how sure you are. If you are not sure, tell me what would decide it.
- Say your disagreement one time, directly and in plain words. Do not lecture, and do not explain what I already know.
- If I still choose my option, do it my way and do not repeat the objection. The rules for actions that are hard to reverse still apply.
- Do not flatter: no "Great question" or "You're right" unless I am right and it matters to the answer.

## Memory
- Search for existing memories also in the project's own `.claude/memory/` and `.claude/memory.local/`.
- Save memories in the project's own `.claude/memory/` by default: shared project knowledge that may be git-committed for the whole team. Save a memory in `.claude/memory.local/` instead only when it is personal ("me only", e.g. my own access details or preferences); that folder is never committed. Each folder keeps its own `MEMORY.md` index.

## Plans
- Search for existing plans also in the project's own `.claude/plans/`.
- Save plans in the project's own `.claude/plans/`. Name new plan files as `YYYY-MM-DD_<hyphen-separated-description>.md` and rename them during the current ongoing conversation as needed as you gather more and more information about the work.

## Comments for code or otherwise
- Prefer code over comments.
- Do not add code comments unless they explan the "why" — explain why, not what.
- Aim to write self-documenting code first, before adding comments. Comments should be your last resort to explain some **VERY** valuable piece of information for future reference, to clarify something that is not immediately obvious, to avoid shooting oneself in the foot, etc.
- When changing existing code, make sure to check the existing comments and ask yourself: is this comment still relevant? If not, remove it. If yes, update it as needed inline with the previous points — when you change code, update or remove the comments near it..
- Do not refer to specific issue or story numbers. Don't quote them.

## Jira wording
- In Jira, Confluence, Slack and git commit text, call a Jira work item a "story", never a "ticket".
- A PreToolUse hook (`~/.claude/hooks/story-not-ticket.py`) enforces this rule. If it denies a call, rewrite the text with "story" and call again.

## Git
- Never rewrite git history, unless explicitly asked to do so by the user.
- A PreToolUse hook (`~/.claude/hooks/guard-git-history.py`) enforces this rule for `rebase`, force pushes, `reset --hard` and `commit --amend`: it denies rewriting a default branch and asks before rewriting anything else. If it denies, do not retry in another form; tell the user.
- Run `git rebase` as its own Bash command, never chained with other commands, and stop if it reports a conflict.
- Never commit uncommitted changes that were already there before you made any changes, nor should you lose'em (e.g., delete'em or `git reset` errorneously, etc.) If they're on your way while doing git operations (eg git commit pre-hook, etc.) you can temporarily stash'em and then when you're done, you should "put them back"

## Running local apps
- When attempting to run local apps, servers, etc. if you hit problems (eg they fail to start), instead of trying to find subpar alternative approaches to work around the real issue, stop and inform the user about the issue and collaborate for a fix before moving on.

## Tool/MCP usage
- When attempting to use tools or MCP, if a given tool or MCP isn't working (eg they fail to start, response, or seem to have setup issues, etc.), instead of trying to find subpar alternative approaches to work around the real issue, stop and inform the user about the issue and collaborate for a fix before moving on.
- For browser automation, prefer the Chrome DevTools MCP (`mcp__plugin_chrome-devtools-mcp_chrome-devtools__*`) over Claude in Chrome (`mcp__claude-in-chrome__*`).

## Scratchpad and temporary files
- Put every temporary file (scripts, screenshots, diffs, command outputs, notes, drafts) in `<project root>/.claude/scratchpad.local/<work-name>/`. Never put them elsewhere in the project.
- A PreToolUse hook (`~/.claude/hooks/guard-paths.py`) denies writes to system temp directories, `~/.claude/plans` and the global auto-memory. If it denies a write, use the path its reason names.
- If `.claude/scratchpad.local/` does not exist, create it with a `.gitignore` that contains only `*`. This keeps it out of git without a change to any shared `.gitignore`.
- Use one `<work-name>` directory per body of work. Pick its name in this order:
  1. The current branch name, if it is not the default branch (replace `/` with `-`).
  2. `<STORY-ID>-<hyphen-separated-description>` if the work has a Jira story, else a short hyphen-separated description, if the work has a clear goal.
  3. `YYYY-MM-DD_<best-guess-description>`, as a last resort.
- If you continue earlier work, reuse its directory. If you are not sure which directory belongs to the work, ask.
- When you spawn subagents, give them the same `<work-name>` path.
- Keep track of temporary files in each session. When you decide the work no longer needs them, delete them without asking the user (deleting means `trash`, see "Deleting files" below).
- Trash the whole `<work-name>` directory with one `trash` call, not file by file, so the Trash holds one folder with all the temporary files of that work.
- To continue earlier work whose `<work-name>` directory is in `~/.Trash`, move it back to `<project root>/.claude/scratchpad.local/` with `mv`; no need to ask. The Trash renames a duplicate name (e.g. `<work-name> 2`): if more than one match exists, compare dates and contents to pick the right one. If the target directory already exists, stop and ask instead of merging or overwriting.

## Deleting files: `trash`, never `rm`

- **Never** delete with `rm`: not `rm -rf`, not `command rm`, not `/bin/rm`, and not their equivalents (`rmdir`, `unlink`, `find -delete`, `xargs rm`, `git clean`, or a script written to do it instead). This includes temporary, scratch and test files — there are no exceptions.
- Use `command trash --stopOnError <path>` (`/usr/bin/trash`). It moves files to the macOS Trash, so every deletion stays recoverable until the user empties it.
- Never empty the Trash or delete anything inside `~/.Trash`. Moving a scratchpad directory out of it to restore it is allowed (see "Scratchpad and temporary files").
- If `trash` is unavailable or fails, stop and ask. Do not fall back to `rm`.
- `permissions.deny` in `settings.json` and a PreToolUse hook (`~/.claude/hooks/deny-deletions.py`) block deletions, including nested ones. Never route a deletion around them.
- Why: a deletion that cannot be undone turns any misjudgment ("it's only a temp file", "that backup isn't needed") into permanent loss.

## Changing how Claude Code works: consult the levers map first

- Before you answer a question about how to customize Claude Code, load the `claude-code-levers` skill and read its map. This includes "which mechanism fits" and "how do we improve CLAUDE.md".
- Do the same before you add or change a Claude Code customization: CLAUDE.md, rules, skills, hooks, settings, subagents, output styles, MCP servers or plugins.
- Pick the lever by the map's "why it exists" column, and say in your answer which lever you picked and why.
- Why: your own knowledge of Claude Code features goes out of date. A scheduled job on one machine (the `work` profile) re-verifies the map against the official docs every week and pushes it; every other machine takes the map from Git. If the map's `last_verified` is older than 30 days, tell me.

## User-level skills live in dotfiles

- `~/.claude/skills/<name>` entries are symlinks into the dotfiles repo: `~/Developer/dotfiles/software/claude-code/skills/<group>/<name>/`. The group is `common` (every machine) or `work` (work profile only).
- Create or edit a user-level skill **in the dotfiles repo**, never as a plain directory in `~/.claude/skills/`. Then link it: `ln -s ~/Developer/dotfiles/software/claude-code/skills/<group>/<name> ~/.claude/skills/<name>` (the dotfiles installer creates the same link on its next run).
- Never replace `~/.claude/skills` itself with a symlink: Claude Code writes the skills it syncs from claude.ai into that directory.

The dotfiles repo is public on GitHub. Its `CLAUDE.md` says what may not go in it; read that before you change a file there.
