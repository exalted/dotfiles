## Working directory
- Make sure to `cd` into the project's root directory (or the relevant git worktree) before running commands

## Referring to numbered items, ids, permalinks in the session (e.g., Q1, RE2, RE Q3, D3, AC-5, Jira-123, etc.)
- Along side the numbered item **ALWAYS** mention also a single-sentence "summary" of what the numbered item is, because in long-lasting conversations it's easy to lose track of what's what.

## Ask clarifying questions
- When needed (e.g., your confidence is lower than 90%), you should ask clarifying questions instead of making assumptions or "calling the shots".
- You should NOT limit yourself to a limited number of questions (e.g., three), instead ask as much questions as possible until satisfied.

## Running commands
- When you/agent/LLM/model runs a well-known/built-in commands (eg grep, cat, sed, awk, date, etc.) make sure to prefix'em with `command` (eg `command date` instead of only `date`) or use `/bin/<command>` to make to run the "raw"/original version and not an alias or a "wrapped"/enhanced version. This rule doesn't apply to managed scripts or commands that the user explicitly runs.
- A PreToolUse hook (`~/.claude/hooks/require-command-prefix.py`) enforces this rule: it denies a Bash command that calls one of the user's shell aliases or functions that hides a real command. If it denies a command, run it again with `command`.
- When you replace a wrapper with `command <name>`, look at what the wrapper added. Keep a flag only if it is a sensible default that matches the user's preferences, for example `--stopOnError` for `trash`. Drop flags that change the output or behavior in ways you would not expect, for example `-F1` for `ls`.

## Running tests
- Never add `-s` / `--capture=no` to a pytest run whose results you intend to read. Capturing is what attaches a failing test's output to its failure report (the `Captured stdout/stderr/log call` sections); `-s` strips those sections and scatters the output through the run, interleaved with every passing test's output.
- `-s` combined with `-n` (pytest-xdist) is worse than either alone: worker stdout is **silently discarded** — it appears neither live nor in the failure report. Verified on pytest + xdist.
- When live output is genuinely wanted (a hanging test, a slow eval), use `--log-cli-level=INFO` for logs, or `--capture=tee-sys`, which streams output *and* keeps the failure report intact. Reserve `-s` for a single test being actively debugged, or where a script parses a passing test's stdout.
- For parallelism, prefer an explicit small worker count (`-n 6`) over `-n auto` on a machine you are also working on. Per-worker startup dominates, so returns saturate quickly and `auto` mostly buys CPU contention.
- Prefer a project's own `make` target or checked-in run configuration over hand-rolled pytest flags — if the target needs different flags, fix the target so everyone gets the fix.

## Writing language
- When producing text in English, for example for code comments, use American English spelling and grammar, instead of British English (eg "color" instead of "colour")
- Write your answers to me in ASD-STE100 Simplified Technical English. Follow it to about 80%, not 100%: apply its main rules, but break a rule when strict compliance makes the text less precise or less clear.
  - Keep sentences short: max 20 words for instructions, max 25 words for descriptions.
  - Use the active voice and the imperative for instructions. Write one instruction per sentence.
  - Use one word for one meaning, and use the same word for the same thing every time. Prefer the STE approved words and their approved meanings.
  - Keep technical names and technical verbs as they are (eg code identifiers, commands, file paths, product names, domain terms).
  - Put conditions first ("If X, do Y"). Use a vertical list for a sequence of steps.

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
- Do not refer to specific issue, ticket, story numbers. Don't quote them.

## Git
- Never rewrite git history, unless explicitly asked to do so by the user.
- Never add Claude as a co-author on git commits (no Co-Authored, Co-Authored-By, etc. in git commit message)
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

## Third-party libraries and frameworks
- Get the latest up-to-date documentation and code using context7 MCP server. use context7

## Deleting files: `trash`, never `rm`

- **Never** delete with `rm`: not `rm -rf`, not `command rm`, not `/bin/rm`, and not their equivalents (`rmdir`, `unlink`, `find -delete`, `xargs rm`, `git clean`, or a script written to do it instead). This includes temporary, scratch and test files — there are no exceptions.
- Use `command trash --stopOnError <path>` (`/usr/bin/trash`). It moves files to the macOS Trash, so every deletion stays recoverable until the user empties it.
- Never empty the Trash or delete anything inside `~/.Trash`. Moving a scratchpad directory out of it to restore it is allowed (see "Scratchpad and temporary files").
- If `trash` is unavailable or fails, stop and ask. Do not fall back to `rm`.
- `permissions.deny` in `settings.json` hard-blocks the direct forms. Indirect ones (`bash -c '…'`, a python or perl one-liner) match no rule, so only this rule stops those: never route a deletion around the deny list.
- Why: a deletion that cannot be undone turns any misjudgment ("it's only a temp file", "that backup isn't needed") into permanent loss.

## User-level skills live in dotfiles

- `~/.claude/skills/<name>` entries are symlinks into the dotfiles repo: `~/Developer/dotfiles/software/claude-code/skills/<group>/<name>/`. The group is `common` (every machine) or `work` (work profile only).
- Create or edit a user-level skill **in the dotfiles repo**, never as a plain directory in `~/.claude/skills/`. Then link it: `ln -s ~/Developer/dotfiles/software/claude-code/skills/<group>/<name> ~/.claude/skills/<name>` (the dotfiles installer creates the same link on its next run).
- Never replace `~/.claude/skills` itself with a symlink: Claude Code writes the skills it syncs from claude.ai into that directory.

### The dotfiles repo is public on GitHub

Before you add or change any file there (skills, scripts, `CLAUDE.md`, settings), check it contains nothing exploitable or personal:

- no secrets, tokens, passwords or API keys;
- no personal data: names combined with contact details, email addresses, phone numbers, user or account IDs;
- no organization-internal identifiers: tenant, client or application IDs, internal hostnames, URLs, IP addresses, Jira sites or project keys, Slack channel links;
- no description of an organization's security setup, such as which permissions are or are not granted.

Write instructions generically. Put organization-specific values in untracked config (for example `~/.config/dotfiles/`), as the repo already does for Jira.

## Eval results (e.g., pydantic-eval)

When you run evals, its results come back and you show the results to me, make sure to add a footnote as close to the eval results as possible which explain the meaning of precision and recall specifically in the context of the work that is being done. Also mention what lower and higher values for each would mean.
