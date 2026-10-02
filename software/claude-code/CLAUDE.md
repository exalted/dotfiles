## Working directory
- Make sure to `cd` into the project's root directory (or the relevant git worktree) before running commands

## Referring to numbered items, ids, permalinks in the session (e.g., Q1, RE2, RE Q3, D3, AC-5, Jira-123, etc.)
- Along side the numbered item **ALWAYS** mention also a single-sentence "summary" of what the numbered item is, because in long-lasting conversations it's easy to lose track of what's what.

## Ask clarifying questions
- When needed (e.g., your confidence is lower than 90%), you should ask clarifying questions instead of making assumptions or "calling the shots".
- You should NOT limit yourself to a limited number of questions (e.g., three), instead ask as much questions as possible until satisfied.

## Running commands
- When you/agent/LLM/model runs a well-known/built-in commands (eg grep, cat, sed, awk, date, etc.) make sure to prefix'em with `command` (eg `command date` instead of only `date`) or use `/bin/<command>` to make to run the "raw"/original version and not an alias or a "wrapped"/enhanced version. This rule doesn't apply to managed scripts or commands that the user explicitly runs.

## Running tests
- Never add `-s` / `--capture=no` to a pytest run whose results you intend to read. Capturing is what attaches a failing test's output to its failure report (the `Captured stdout/stderr/log call` sections); `-s` strips those sections and scatters the output through the run, interleaved with every passing test's output.
- `-s` combined with `-n` (pytest-xdist) is worse than either alone: worker stdout is **silently discarded** — it appears neither live nor in the failure report. Verified on pytest + xdist.
- When live output is genuinely wanted (a hanging test, a slow eval), use `--log-cli-level=INFO` for logs, or `--capture=tee-sys`, which streams output *and* keeps the failure report intact. Reserve `-s` for a single test being actively debugged, or where a script parses a passing test's stdout.
- For parallelism, prefer an explicit small worker count (`-n 6`) over `-n auto` on a machine you are also working on. Per-worker startup dominates, so returns saturate quickly and `auto` mostly buys CPU contention.
- Prefer a project's own `make` target or checked-in run configuration over hand-rolled pytest flags — if the target needs different flags, fix the target so everyone gets the fix.

## Writing language
- When producing text in English, for example for code comments, use American English spelling and grammar, instead of British English (eg "color" instead of "colour")

## Memory
- Search for existing memories also from project's own working directory: both `.claude/memory/` and `.claude/memory.local/`
- *IMPORTANT*: Always save memories in the project's own working directory (`.claude/memory/`) and *never* in `~/.claude/`. This keeps memories colocated with the project they belong to.
- `.claude/memory/` is the default for new memories: shared project knowledge that may be git-committed for the whole team. Save a memory in `.claude/memory.local/` instead only when it is personal ("me only", e.g. my own access details or preferences); that folder is never committed. Each folder keeps its own `MEMORY.md` index.

## Plans
- Search for existing plans also from project's own working directory (`.claude/plans/`)
- *IMPORTANT*: Always save plans in the project's own working directory (`.claude/plans/`) and *never* in `~/.claude/`. This keeps plans colocated with the project they belong to.
- Name new plan files as `YYYY-MM-DD_<hyphen-separated-description>.md` and rename them during the current ongoing conversation as needed as you gather more and more information about the work.

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
- If you need to create temporary files, create them in a dedicated directory within the current working directory as described above instead of the system's temp directory (e.g. /tmp/, /private/tmp/, etc.) — do not create plans, scripts, screenshots, diffs, command outputs, scratchpad, etc. outside the current working directory.
- Keep track of temporary files in each session and at the end of the session ask the user whether to keep them around or delete them (deleting means `trash`, see "Deleting files" below).

## Third-party libraries and frameworks
- Get the latest up-to-date documentation and code using context7 MCP server. use context7

## Deleting files: `trash`, never `rm`

- **Never** delete with `rm`: not `rm -rf`, not `command rm`, not `/bin/rm`, and not their equivalents (`rmdir`, `unlink`, `find -delete`, `xargs rm`, `git clean`, or a script written to do it instead). This includes temporary, scratch and test files — there are no exceptions.
- Use `trash <path>` (`/usr/bin/trash`). It moves files to the macOS Trash, so every deletion stays recoverable until the user empties it.
- Never empty the Trash or delete anything inside `~/.Trash`.
- If `trash` is unavailable or fails, stop and ask. Do not fall back to `rm`.
- `permissions.deny` in `settings.json` hard-blocks the direct forms. Indirect ones (`bash -c '…'`, a python or perl one-liner) match no rule, so only this rule stops those: never route a deletion around the deny list.
- Why: a deletion that cannot be undone turns any misjudgment ("it's only a temp file", "that backup isn't needed") into permanent loss.

## Eval results (e.g., pydantic-eval)

When you run evals, its results come back and you show the results to me, make sure to add a footnote as close to the eval results as possible which explain the meaning of precision and recall specifically in the context of the work that is being done. Also mention what lower and higher values for each would mean.
