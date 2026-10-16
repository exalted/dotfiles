---
name: claude-code-levers
description: Map of Claude Code's customization levers (CLAUDE.md, rules, settings, hooks, skills, subagents, MCP, plugins, output styles, permission modes, headless mode, SDK, ...) with the one reason each exists. Use when the user asks how to customize, extend, configure, or automate Claude Code, which mechanism fits a need (for example hook vs CLAUDE.md vs skill vs subagent), or what levers exist. Also use before adding or changing any customization (CLAUDE.md, rules, skills, hooks, settings, subagents, output styles), even when the user did not ask which lever to use. Run with `refresh` to re-verify the map against the official docs, add new levers, and retire superseded ones.
argument-hint: "[refresh]"
---

# Claude Code levers

A **lever** is a built-in mechanism of Claude Code that you configure to change what it knows, what it may do, how it behaves, or how it runs. The map lives in `references/levers.md`: one row per lever with the single reason it exists (its main use case), what the sources teach about using it, where it is configured, and the sources it was distilled from. The map is the knowledge: nobody, human or Claude, is expected to open the sources to use it. The scheduled `refresh` keeps it current so that a question is answered from the map, fast.

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
2. Answer from the map. Pick the lever by the first sentence of its **why it exists** column, not by familiarity. Mistakes the map prevents: enforcing behavior with CLAUDE.md (use a hook), storing reference knowledge in CLAUDE.md (use a skill), running a wide search in the main context (use a subagent).
3. Open a source only when the map does not answer the question. Read the page from the mirror if it is there, else fetch it with `scripts/fetch-page.sh <url>`, which works on any machine. Delegate to the `claude-code-guide` agent only for depth beyond the sources. Then record the gap: add one line to the map's **Watch** section with the question, the source that answered it, and today's date, and leave it uncommitted. The next `refresh` distills it into a row, so the same question is answered from the map next time.

## `refresh`: challenge the map

Run when invoked as `/claude-code-levers refresh`, or when `last_verified` in `references/levers.md` is older than 30 days and the user agrees. The run is non-interactive: ask no questions, commit nothing. (The scheduled job, installed on the `work` profile only, commits and pushes the map by itself after the run. Every other machine takes the map from Git and keeps no refresh job, docs mirror or log.)

Three sources, with different authority:

- **The docs** are the source of truth. A mechanism and its configuration surface enter a row only after a docs page confirms them.
- **The changelog** (`en/changelog.md` in the mirror) and **the blog** (`blog/` in the mirror) are signals. They point at what to check, and a post may teach how to use a lever, which the row then says in its own words with the post as a source. Neither puts a mechanism into a row by itself: something can change without an entry, and an entry can name something the docs do not have yet.

1. Read `references/levers.md`.
2. Mirror the sources: run `scripts/sync-docs.sh` from this skill's directory. It downloads every English docs page as Markdown into `<dotfiles>/.claude/scratchpad.local/claude-code-levers/docs/`, where `<dotfiles>` is the repository this skill is checked out in, and every claude.dev post into `blog/` below it, and prints that path. No single index is complete, so the page list in the mirror's `.pages` is the union of `llms.txt`, the sitemap, and every page linked from a mirrored page; treat `llms.txt` and the sitemap as hints, never as the full index. If the command is denied (the scheduled job has synced already), use the mirror as it is. The mirror is only as fresh as its `.synced` timestamp: a refresh always syncs first, so it never reads stale pages by design. A doc URL maps to a mirror file by its path after `/docs/`: `https://code.claude.com/docs/en/hooks.md` is `en/hooks.md`. A post maps to `blog/<slug>.md`.
3. Triage the signals: run `scripts/triage.sh` from this skill's directory and keep its output for the agent. It takes the changelog entries and the posts dated on or after `last_verified` and prints, per text, the configuration surfaces it names, sorted into **known** (the map names it), **documented-unmapped** (a docs page names it, the map does not) and **undocumented** (neither does). A text with nothing in the last two bins cannot change a row, whatever its title; at most it teaches how to use a mapped lever.
4. Spawn one agent with the full table, the mirror path and the triage output: `claude-code-guide` if it is listed, else `general-purpose`. Bound its work:
   - Read pages from the mirror with the Read and Grep tools, not with `grep` in Bash, which a headless run denies.
   - A page the mirror lacks is fetched in this order, and only the first way that works is used:
     1. `scripts/fetch-page.sh <url>` from this skill's directory. It saves the page as Markdown into the mirror, whole, and prints the file's path. Read that file.
     2. WebFetch on the URL with `.md` appended, which the site serves as Markdown. WebFetch cuts a page at about 100k characters: mark the row † if the page came back truncated.
     3. WebFetch on the plain URL, the HTML page, as the last resort. Same cut, same † rule.
   - Read long pages by section. The hooks, settings, MCP, CLI and environment references are over 100k characters: Grep the headings (`^#{1,3} `) first, then Read only the section the row needs, with an offset and a limit. Never read such a page whole.
   - Verify each row against its sources and report it as confirmed, changed (with the correction), superseded (by what), or gone. Rows marked † count as unread; read them.
   - For each documented-unmapped surface in the triage output: read the docs section that names it and report where it belongs: a row's Where cell, a merge into a row, a new row, or nowhere (an internal detail). For each undocumented one: report it for Watch with its source and date, or as noise.
   - For each post in the triage output: report what it teaches about using a mapped lever that the row does not say yet, in one to three sentences in the row's own words, with the post as a source. Skip what the docs page already says, and skip what is not about a lever: models, prices, performance stories, general practice.
   - For each line in Watch: check the mirror again and report it as covered (with the docs page), still uncovered, or stale.
   - For new levers, read `.pages` in the mirror, the complete page list, and open only pages whose title names a mechanism you configure: settings, hooks, skills, agents, modes, tools, integrations. Skip installation, authentication, billing, terminal and UI how-tos, troubleshooting, enterprise deployment, and reference tables.
   - Then run a few WebSearch queries limited to `site:code.claude.com/docs` for mechanisms the map or the page list may miss, for example new settings keys, hook events or modes. Fetch any docs page a result names that the mirror lacks with `fetch-page.sh` and treat it like a mirrored page.
   - Only if the whole mirror is missing and `fetch-page.sh` fails too: use WebFetch in the order above and cap the job at about 90 fetches.
   - Require a docs page for every mechanism and every configuration surface. A post may be the source only of how to use a lever. Reject claims from memory.
5. Apply the result to `references/levers.md`:
   - Update changed rows. The first sentence of "why it exists" stays the single purpose; the sentences after it carry what the sources teach, in the row's own words.
   - Add new levers. Add a post to a row's Sources only when the row says something taken from it.
   - Move superseded or removed levers to the **Retired** section with today's date and the successor. Drop a Retired row at the next refresh after the one that added it.
   - Update **Watch**: add the new lines, turn covered lines into rows, drop lines older than 90 days.
   - Set `last_verified` to today.
6. Keep the file generic. It lives in a public repo: no personal data, no organization identifiers.
7. Leave the changes uncommitted. Print one thing only: a short summary of rows changed, added, retired, Watch lines added or resolved, and anything the agent could not verify, with no preamble about what you did or did not commit. The scheduled job stores that output verbatim as the body of the map's commit message, so it has the same public-repo rule as the file, and it must explain the changes well enough that the commit makes sense on its own.
