---
name: claude-code-levers
description: Map of Claude Code's customization levers (CLAUDE.md, rules, settings, hooks, skills, subagents, MCP, plugins, output styles, permission modes, headless mode, SDK, ...) with the one reason each exists. Use when the user asks how to customize, extend, configure, or automate Claude Code, which mechanism fits a need (for example hook vs CLAUDE.md vs skill vs subagent), or what levers exist. Also use before adding or changing any customization (CLAUDE.md, rules, skills, hooks, settings, subagents, output styles), even when the user did not ask which lever to use. Run with `refresh` to re-verify the map against the official docs, add new levers, and retire superseded ones.
argument-hint: "[refresh]"
---

# Claude Code levers

A **lever** is a built-in mechanism of Claude Code that you configure to change what it knows, what it may do, how it behaves, or how it runs. The map lives in `references/levers.md`: one row per lever with the single reason it exists (its main use case), where it is configured, and the doc URL.

Not a lever, so not a row: a product surface (the Desktop app, the web app, an IDE extension), an explanatory page (context window, caching, security model), account and billing matters, UI how-tos (setup walkthroughs, dictation, accessibility), and enterprise deployment plumbing (proxies, gateways, launchers, telemetry). A single row may point to several of those pages when the user needs them. The map stays under about 60 rows: merge into an existing row before adding one, and add a row only for a mechanism a user configures, not for every doc page.

## Not the same as

| Term | What it is | Relation to levers |
|---|---|---|
| Plugin | An installable bundle of skills, agents, hooks, MCP servers, LSP servers | A plugin *ships* levers. Distribution is itself one lever. |
| Extension | The IDE extensions (VS Code, JetBrains) and the Chrome extension | A surface where Claude Code runs. Not a lever. |
| Connector | A claude.ai integration (chat, tickets, observability, ...) exposed as an MCP server | One source of MCP servers. The lever is MCP, not the connector. |

Say "lever", not "extension point", so these do not blur.

## Answer a question

1. Read `references/levers.md`.
2. Pick the lever by its **why it exists** column, not by familiarity. Mistakes the map prevents: enforcing behavior with CLAUDE.md (use a hook), storing reference knowledge in CLAUDE.md (use a skill), running a wide search in the main context (use a subagent).
3. If the question needs more depth than the map, delegate to the `claude-code-guide` agent. The map is deliberately shallow.

## `refresh`: challenge the map

Run when invoked as `/claude-code-levers refresh`, or when `last_verified` in `references/levers.md` is older than 30 days and the user agrees. The run is non-interactive: ask no questions, commit nothing. (The scheduled job, installed on the `work` profile only, commits and pushes the map by itself after the run. Every other machine takes the map from Git and keeps no refresh job, docs mirror or log.)

1. Read `references/levers.md`.
2. Mirror the docs: run `scripts/sync-docs.sh` from this skill's directory. It downloads every English docs page as Markdown into `<dotfiles>/.claude/scratchpad.local/claude-code-levers/docs/`, where `<dotfiles>` is the repository this skill is checked out in, and prints that path. No single index is complete, so the page list in the mirror's `.pages` is the union of `llms.txt`, the sitemap, and every page linked from a mirrored page; treat `llms.txt` and the sitemap as hints, never as the full index. If the command is denied (the scheduled job has synced already), use the mirror as it is. The mirror is only as fresh as its `.synced` timestamp: a refresh always syncs first, so it never reads stale pages by design. A doc URL maps to a mirror file by its path after `/docs/`: `https://code.claude.com/docs/en/hooks.md` is `en/hooks.md`.
3. Spawn one agent with the full table and the mirror path: `claude-code-guide` if it is listed, else `general-purpose`. Bound its work:
   - Read pages from the mirror with the Read and Grep tools, not with `grep` in Bash, which a headless run denies.
   - A page the mirror lacks is fetched in this order, and only the first way that works is used:
     1. `scripts/fetch-page.sh <url>` from this skill's directory. It saves the page as Markdown into the mirror, whole, and prints the file's path. Read that file.
     2. WebFetch on the URL with `.md` appended, which the site serves as Markdown. WebFetch cuts a page at about 100k characters: mark the row † if the page came back truncated.
     3. WebFetch on the plain URL, the HTML page, as the last resort. Same cut, same † rule.
   - Read long pages by section. The hooks, settings, MCP, CLI and environment references are over 100k characters: Grep the headings (`^#{1,3} `) first, then Read only the section the row needs, with an offset and a limit. Never read such a page whole.
   - Verify each row against its page and report it as confirmed, changed (with the correction), superseded (by what), or gone. Rows marked † count as unread; read them.
   - For new levers, read `.pages` in the mirror, the complete page list, and open only pages whose title names a mechanism you configure: settings, hooks, skills, agents, modes, tools, integrations. Skip installation, authentication, billing, terminal and UI how-tos, troubleshooting, enterprise deployment, and reference tables.
   - Then run a few WebSearch queries limited to `site:code.claude.com/docs` for mechanisms the map or the page list may miss, for example new settings keys, hook events or modes. Fetch any docs page a result names that the mirror lacks with `fetch-page.sh` and treat it like a mirrored page.
   - Only if the whole mirror is missing and `fetch-page.sh` fails too: use WebFetch in the order above and cap the job at about 90 fetches.
   - Require a doc page for every claim; reject claims from memory.
4. Apply the result to `references/levers.md`:
   - Update changed rows. Keep "why it exists" to one sentence.
   - Add new levers.
   - Move superseded or removed levers to the **Retired** section with today's date and the successor. Drop a Retired row at the next refresh after the one that added it.
   - Set `last_verified` to today.
5. Keep the file generic. It lives in a public repo: no personal data, no organization identifiers.
6. Leave the changes uncommitted. Print one thing only: a short summary of rows changed, added, retired, and anything the agent could not verify, with no preamble about what you did or did not commit. The scheduled job stores that output verbatim as the body of the map's commit message, so it has the same public-repo rule as the file, and it must explain the changes well enough that the commit makes sense on its own.
