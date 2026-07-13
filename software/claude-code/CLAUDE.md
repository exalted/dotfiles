## Working directory
- Make sure to `cd` into the project's root directory (or the relevant git worktree) before running commands

## Writing language
- When producing text in English, for example for code comments, use American English spelling and grammar, instead of British English (eg "color" instead of "colour")

## Memory
- Search for existing memories also from project's own working directory (`.claude/memory/`)
- *IMPORTANT*: Always save memories in the project's own working directory (`.claude/memory/`) and *never* in `~/.claude/`. This keeps memories colocated with the project they belong to.

## Plans
- Search for existing plans also from project's own working directory (`.claude/plans/`)
- *IMPORTANT*: Always save plans in the project's own working directory (`.claude/plans/`) and *never* in `~/.claude/`. This keeps plans colocated with the project they belong to.
- Name new plan files as `YYYY-MM-DD_<hyphen-separated-description>.md` and rename them during the current ongoing conversation as needed as you gather more and more information about the work.

## Comments for code or otherwise
- Do not add code comments unless they explan the "why" — explain why, not what.
- Aim to write self-documenting code first, before adding comments. Comments should be your last resort to explain some **VERT** valuable piece of information for future reference, to clarify something that is not immediately obvious, to avoid shooting oneself in the foot, etc.
- When changing existing code, make sure to check the existing comments and ask yourself: is this comment still relevant? If not, remove it. If yes, update it as needed inline with the previous points — when you change code, update or remove the comments near it..

## Git
- Never rewrite git history, unless explicitly asked to do so by the user.
- Never add Claude as a co-author on git commits.

## Running local apps
- When attempting to run local apps, servers, etc. if you hit problems (eg they fail to start), instead of trying to find subpar alternative approaches to work around the real issue, stop and inform the user about the issue and collaborate for a fix before moving on.

## Tool/MCP usage
- When attempting to use tools or MCP, if a given tool or MCP isn't working (eg they fail to start, response, or seem to have setup issues, etc.), instead of trying to find subpar alternative approaches to work around the real issue, stop and inform the user about the issue and collaborate for a fix before moving on.
- For browser automation, prefer the Chrome DevTools MCP (`mcp__plugin_chrome-devtools-mcp_chrome-devtools__*`) over Claude in Chrome (`mcp__claude-in-chrome__*`).

## Scratchpad and temporary files
- If you need to create temporary files, create them in a dedicated directory within the current working directory as described above instead of inside the system's temp directory (e.g. /tmp/, /private/tmp/, etc.) — do not create plans, scripts, screenshots, diffs, command outputs, scratchpad, etc. outside the current working directory.
- Keep track of temporary files in each session and at the end of the session ask the user whether to keep them around or delete them.

## Third-party libraries and frameworks
- Get the latest up-to-date documentation and code using context7 MCP server. use context7

## `trash` instead of `rm`

When removing files, especially those that NOT temporary files, prefer using `trash` command which should be available in user's shell, which should move the file to the macOS's trash instead of permanently deleting it.
