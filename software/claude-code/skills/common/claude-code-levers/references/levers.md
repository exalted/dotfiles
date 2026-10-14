---
last_verified: 2026-10-14
docs_root: https://code.claude.com/docs/en/
---

# Claude Code levers

One row per lever. "Why it exists" is the single main use case; pick a lever by that column. Doc URLs are relative to `docs_root` unless absolute. A trailing † marks a URL taken from the docs index whose page has not been read yet; the next `refresh` reads it.

## What Claude knows

| Lever | Why it exists | Where | Docs |
|---|---|---|---|
| CLAUDE.md | Standing context Claude cannot infer from code: conventions, commands, team rules. It is context, not enforcement. | `~/.claude/CLAUDE.md`, `./CLAUDE.md`, `./.claude/CLAUDE.md`, `./CLAUDE.local.md`; managed-policy `CLAUDE.md` or the `claudeMd` key; `AGENTS.md` (read only when no `CLAUDE.md` or `CLAUDE.local.md` exists by default; Project instructions in `/config`); `@path` imports (max 4 hops); `claudeMdExcludes` | memory.md |
| Rules | Keep instructions modular. A `paths:` rule loads only when matching files are read or edited, so CLAUDE.md stays small. | `.claude/rules/**/*.md`, `~/.claude/rules/` | memory.md |
| Auto-memory | Keep facts across sessions without you writing them down. | `~/.claude/projects/<project>/memory/` (`MEMORY.md` index, first 200 lines or 25KB load), `/memory`, `autoMemoryEnabled`, `autoMemoryDirectory` | memory.md |
| Skills | Package a repeatable workflow or a body of reference knowledge. Loaded on demand, by name or when relevant. Custom commands are merged into skills. | `.claude/skills/<name>/SKILL.md` (also nested dirs and `--add-dir` roots), `~/.claude/skills/`, `~/.claude/skills/synced/` (from claude.ai), managed, plugins; bundled ones such as `/run` and `/verify`; `/skills`, `/reload-skills`; frontmatter `paths`, `context: fork`, `hooks` | skills.md |
| Output styles | Set role and tone for every response at system-prompt level, without touching the project. Not enforced. | `/output-style`, `.claude/output-styles/`, `~/.claude/output-styles/`, plugins, `outputStyle` | output-styles.md |

## What Claude may do

| Lever | Why it exists | Where | Docs |
|---|---|---|---|
| Settings | Decide once what Claude may do, share it via git, let admins enforce it. | Five scopes, highest first: managed, `--settings`, `.claude/settings.local.json`, `.claude/settings.json`, `~/.claude/settings.json`; `/update-config` writes them; `attribution`, `includeGitInstructions` | settings.md, settings-reference.md |
| Permission rules | Allow, ask, or deny specific tool uses deterministically, independent of the mode. Deny wins, except that an installed mod can approve a denied call where no managed settings apply. | `permissions.allow`, `ask`, `deny` with `Tool(specifier)`; `/permissions`; `--allowedTools`, `--disallowedTools`; `permissions.additionalDirectories` (file access only); `/fewer-permission-prompts` writes an allowlist to `.claude/settings.json` | permissions.md |
| Permission modes | Match trust to the task. | `default` (shown as Manual, alias `manual`), `acceptEdits`, `plan`, `auto`, `dontAsk`, `bypassPermissions`; `auto` is the starting mode in the terminal and VS Code; `auto` and `bypassPermissions` are ignored in project and local settings | permission-modes.md |
| Auto mode configuration | Tell the auto-mode classifier what is trusted. | `autoMode` block: `environment`, `allow`, `soft_deny`, `hard_deny`, `classifyAllShell`; read from user settings, managed settings, or `--settings` only; `claude auto-mode` (`defaults`, `config`, `critique`, `reset`), `/auto-mode-setup` | auto-mode-config.md |
| Sandbox | OS-enforced filesystem and network limits for shell commands and their child processes. Does not cover file tools, MCP servers, hooks, or LSP servers. For a boundary around the whole process, use the sandbox runtime or a dev container. | `sandbox` in settings, `/sandbox`; macOS, Linux, WSL2; `npx @anthropic-ai/sandbox-runtime claude` (research preview); `.devcontainer/` with the official feature | sandboxing.md, sandbox-environments.md, devcontainer.md |

## Enforce and shape the harness

| Lever | Why it exists | Where | Docs |
|---|---|---|---|
| Hooks | Enforce behavior deterministically. CLAUDE.md is advice; a hook always runs. `PreToolUse` runs before every tool call and before permission rules are evaluated; an installed mod can override a non-managed block. | `hooks` in settings, skill and subagent frontmatter, plugin `hooks/hooks.json`; `/hooks`; 33 events; handler types `command`, `http`, `mcp_tool`, `prompt`, `agent` (experimental); `disableAllHooks` | hooks.md, hooks-guide.md |
| Mods | Code that runs inside Claude Code: draw panes and bands, add commands, intercept tool calls and prompts. Hooks and skills cannot draw UI. | JS/TS hooks module in a plugin (`hooks/hooks.json` plus `register.js`); on by default; installed mods off with `--safe-mode`, `--bare`, or `disableAllHooks`; built-in mods (`/diff` is `cc-plugin-diff`, also the AGENTS.md loader and You should know) are toggled only in `/plugin` | plugins/mods/overview.md |
| Status line | Show the session context you care about below the prompt, one row per line your script prints. | `statusLine` (`command`, `padding`, `refreshInterval`), `/statusline`; receives session JSON on stdin; `subagentStatusLine` | statusline.md |
| Keybindings | Rebind keys, including chords. Applied without restart. | `~/.claude/keybindings.json`, `/keybindings` | keybindings.md |
| Terminal | Match the terminal: theme, notifications, Vim editing, fullscreen renderer, voice input, screen reader. | `/theme`, `~/.claude/themes/<slug>.json`; `/terminal-setup`; `preferredNotifChannel`; `editorMode: "vim"`; `/tui fullscreen` (research preview); `/voice`; `--ax-screen-reader` | terminal-config.md, interactive-mode.md, fullscreen.md, voice-dictation.md, accessibility.md |

## Scale out

| Lever | Why it exists | Where | Docs |
|---|---|---|---|
| Subagents | Isolate work in a separate context window. Restrict tools and model per role. | `.claude/agents/*.md`, `~/.claude/agents/`, `--agents` JSON, plugin `agents/`; built-ins Explore, Plan, general-purpose, `claude`, `claude-code-guide`, `statusline-setup`; `--agent` or the `agent` setting runs the main thread as one; fork mode lets Claude spawn subagents that inherit the conversation (on in interactive sessions, `CLAUDE_CODE_FORK_SUBAGENT`, `/subtask`) | sub-agents.md |
| Workflows | Orchestrate many subagents deterministically from a JavaScript script. | `Workflow` tool, `/workflows`, `ultracode` (keyword, `/effort ultracode`, setting); saved under `.claude/workflows/` or `~/.claude/workflows/`; `disableWorkflows`, `enableWorkflows`, `workflowSizeGuideline`; paid plans (on Pro, turn on in `/config`) | workflows.md |
| Agent teams (experimental) | Teammates with separate contexts, a shared task list, and messaging. For work that needs debate or cross-checking. | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, `teammateMode` | agent-teams.md |
| Worktrees | Parallel work without collisions in one checkout. | `--worktree` (`-w`), `isolation: worktree` on subagents, `worktree.baseRef`, `worktree.sparsePaths`, `worktree.symlinkDirectories`; `.worktreeinclude`; `WorktreeCreate` and `WorktreeRemove` hooks; `/batch` splits one change across worktree-isolated subagents | worktrees.md, large-codebases.md |
| Cross-session messaging | Pass findings between separate sessions you run. | On by default; `ListAgents` and `SendMessage` tools, `/list-agents`, `@session` mentions; `crossSessionInbound` (`accept`, `hold`, `refuse`); cross-machine needs Remote Control | cross-session-messaging.md |
| Sessions | Name, resume, fork, and switch conversations. | `/branch`, `/rename`, `/resume`, `/export`; `--resume`, `--continue`, `--fork-session`, `--from-pr`, `--name`; transcripts in `~/.claude/projects/<project>/`; `cleanupPeriodDays`; deep links `claude-cli://open?cwd=…&repo=…&q=…` | sessions.md, deep-links.md |
| Projects (public beta) | One coordinating conversation that runs parallel cloud threads with shared instructions and memory. | claude.ai/code or the Desktop Code tab; Pro and Max | claude-projects.md |

## Repeat and keep going

| Lever | Why it exists | Where | Docs |
|---|---|---|---|
| `/loop` | Repeat a prompt on a time interval inside one session. Fires only while the session runs; expires 7 days after creation. | bundled skill (alias `/proactive`); default prompt in `.claude/loop.md` or `~/.claude/loop.md`; min interval 1 min; `CLAUDE_CODE_DISABLE_CRON=1`; to react to events instead of polling, the `Monitor` tool streams a background command | scheduled-tasks.md, tools-reference.md |
| `/goal` | Keep working until a completion condition holds. A small fast model checks the condition after each turn. | `/goal`, `/goal clear`; a prompt-based Stop hook underneath; `CLAUDE_CODE_GOAL_CHECKIN_MINUTES` | goal.md |
| Routines (research preview) | Run an agent on Anthropic's cloud on a schedule, API call, or GitHub event. No local machine needed; cannot touch local files. | `/schedule` (alias `/routines`), claude.ai/code/routines, Desktop Routines > New routine > Cloud; min interval 1 hour | routines.md |
| Desktop scheduled tasks | Run a prompt on your machine on a schedule, with local file access and per-task permissions. No open session needed; the desktop app and the machine must be on. | Desktop app: Code tab, Routines, New routine, Local. Prompt on disk at `~/.claude/scheduled-tasks/<name>/SKILL.md` | desktop-scheduled-tasks.md |
| Channels (research preview) | Push external events (chat, CI, webhooks) into a running session so Claude reacts while you are away. | stdio MCP server with the `experimental['claude/channel']` capability, installed as a plugin; `claude --channels plugin:<name>@<marketplace>`; managed `channelsEnabled`, `allowedChannelPlugins`; the pre-built plugins need Bun; claude.ai or Console auth only, not Bedrock, Agent Platform, or Foundry | channels.md, channels-reference.md |

## Connect

| Lever | Why it exists | Where | Docs |
|---|---|---|---|
| MCP servers | Connect to external systems through one standard protocol. | `.mcp.json` (project), `~/.claude.json` (local, user), `claude mcp add`; scopes local, project, user; transports `http`, `stdio`, `ws` (config file or `claude mcp add-json` only; `sse` deprecated; `sdk` only from an SDK host app); `--mcp-config`, `--strict-mcp-config`; `@server:uri` resources; `ENABLE_TOOL_SEARCH`, `alwaysLoad`, `MAX_MCP_OUTPUT_TOKENS` | mcp.md |
| Plugins | Distribute skills, agents, hooks, mods, monitors, MCP servers, LSP servers, channels, workflows, output styles, themes, default settings (`agent` and `subagentStatusLine` only), and `bin/` executables as one installable bundle. | `/plugin install name@marketplace` or `claude plugin install`; install scopes user, project, local (`managed` is admin-only); `--plugin-dir`; dependencies with version ranges; `claude plugin eval` scores a plugin | plugins/components.md, plugins/install.md, plugins/dependencies.md, plugin-evals.md |
| LSP servers | Give Claude language-server intelligence: diagnostics after edits, read-only navigation. | via plugins, `.lsp.json`; official `*-lsp` plugins; not in cloud sessions | plugins/code-intelligence.md |
| Browser and desktop control | Act in a real browser or on the desktop. | Chrome: off by default, `--chrome` or the Enabled by default toggle in `/chrome`, extension required, paid plan with `/login` (not an API key); computer use: research preview, macOS CLI only, Pro and Max, interactive sessions only, enable the `computer-use` server in `/mcp` | chrome.md, computer-use.md |
| Artifacts | Publish session output as a live page on claude.ai that updates in place and that others can open and comment on. | `Artifact` tool, `/artifacts`; `/slides` and `/design` templates (beta); off with `enableArtifact` in `/config`, `CLAUDE_CODE_DISABLE_ARTIFACT=1`, or a deny rule; paid plan with `/login`, Anthropic API only | artifacts.md |

## Run elsewhere or programmatically

| Lever | Why it exists | Where | Docs |
|---|---|---|---|
| Headless mode | Run Claude Code as a component in scripts and CI, with structured output. | `claude -p`, `--output-format`, `--json-schema`, `--allowedTools`, `--permission-prompts none`, `--bare` (future default for `-p`); `--append-system-prompt[-file]`, `--system-prompt[-file]` | headless.md, cli-reference.md |
| Agent SDK | Build your own agent on the same harness. | `claude-agent-sdk` (Python), `@anthropic-ai/claude-agent-sdk` (TypeScript; `query()`, the V2 session API is removed) | agent-sdk/overview.md, agent-sdk/quickstart.md |
| GitHub Actions, GitLab CI | Act on PRs and issues from a mention or on a schedule, without a developer session. | `/install-github-app`, `anthropics/claude-code-action@v1`; GitLab is beta | github-actions.md, gitlab-ci-cd.md |
| Code and security review | Review PRs automatically in GitHub without a workflow file (research preview, Team and Enterprise), review the current diff from a session, or scan code for security issues. | GitHub: an org owner enables it in claude.ai admin settings, `@claude review`, tune with `CLAUDE.md` or `REVIEW.md`; session: `/code-review` (alias `/review`), `/code-review ultra` (alias `/ultrareview`), `claude ultrareview`; security: `/security-review`, the `security-guidance` plugin (checks while Claude writes code), the `claude-security` plugin (`/claude-security` multi-agent scan) | code-review.md, ultrareview.md, security-guidance.md, claude-security.md |
| Claude Code on the web | Run in a cloud sandbox cloned from GitHub. Its environment decides what a session can reach and run: network level, env vars, setup script, secrets, or your own runners. | claude.ai/code, `claude --cloud`; `--teleport` and `/teleport` pull a cloud session local; `/web-setup`; environment selector, `/remote-env`; `claude self-hosted-runner` (public beta, Team and Enterprise) | claude-code-on-the-web.md, cloud-environments.md, self-hosted-environments.md |
| Remote Control | Drive a local session from claude.ai or the mobile app. | `claude --remote-control` (`--rc`), `/rc`, `claude remote-control` (server mode); `remoteControlAtStartup`, `disableRemoteControl`; push notifications in `/config` | remote-control.md |
| Claude Tag (public beta) | Claude as a teammate in Slack threads, each backed by a cloud sandbox with admin-configured connectors and plugins. Team and Enterprise. | claude.ai admin settings, then `@Claude connect` in Slack; Pro and Max workspaces use Claude Code in Slack (`/install-slack-app`, slack.md) instead | https://claude.com/docs/claude-tag/overview †, slack.md |
| Agent view (research preview) | See and manage background sessions in one place. | `claude agents`, `claude --bg`, `/background`; `claude attach`, `logs`, `stop`, `rm`, `respawn`; `disableAgentView` | agent-view.md |

## Tune the model

| Lever | Why it exists | Where | Docs |
|---|---|---|---|
| Model, effort, fast mode, advisor | Trade cost and speed against capability. Advisor (experimental) lets Claude consult a stronger model at decision points. | `/model`; `/effort`, `--effort`: `low`, `medium`, `high`, `xhigh`, `max` (`/effort auto` clears the saved level); `/effort` saves `low` to `xhigh` per model in `modelSettings`, `effortLevel` is the fallback default; `maxEffortLevel` caps an org; `/fast` (research preview; Opus 5.5, Opus 5, Opus 4.8; Anthropic API or subscription), `fastMode`; `/advisor`, `--advisor`, `advisorModel` (Anthropic API only) | model-config.md, fast-mode.md, advisor.md |
| Context and cache | Decide when compaction happens and how long the prompt cache lives. | `/compact`, `/context`, `/autocompact`, `autoCompactWindow`, `autoCompactEnabled`; `promptCacheTtl`, `subagentPromptCacheTtl`; `MAX_THINKING_TOKENS`, `alwaysThinkingEnabled` | model-config.md, prompt-caching.md, context-window.md |
| Environment variables | Tune runtime behavior outside settings: model, effort, timeouts, feature toggles. | `ANTHROPIC_MODEL`, `CLAUDE_CODE_EFFORT_LEVEL`, `BASH_DEFAULT_TIMEOUT_MS`, `CLAUDE_CODE_DISABLE_*` | env-vars.md |

## Recover

| Lever | Why it exists | Where | Docs |
|---|---|---|---|
| Plan mode | Agree on an approach before any edit. | `plan` permission mode, `/plan`, `--permission-mode plan`; `useAutoModeDuringPlan` | permission-modes.md |
| Checkpoints | Undo Claude's file-tool edits without git. Bash changes and most subagent edits are not restored. | `/rewind` (aliases `/checkpoint`, `/undo`), Esc twice; last 100 checkpoints; snapshots swept after `cleanupPeriodDays` (30 days); `fileCheckpointingEnabled` | checkpointing.md |
| Safe and restricted modes | Start with every customization off to find the one that misbehaves, or lock a session down for an eval harness. | `--safe-mode`, `--restricted`, `--tools`, `--setting-sources`; `/doctor` | cli-reference.md |

## Administer

| Lever | Why it exists | Where | Docs |
|---|---|---|---|
| Managed settings | Admin policy with the highest precedence. Users cannot override it, except keys that are defaults, not locks, such as `model`. | `managed-settings.json` and `managed-settings.d/` in the system policy directory; MDM profile or registry; server-managed settings from the claude.ai console (Team and Enterprise); `managedSourcesBehavior`, `policyHelper` | managed-settings.md, server-managed-settings.md |
| Managed MCP | Admin control of which MCP servers users may run. | `managed-mcp.json` (exclusive control; an empty map disables MCP); `managedMcpServers`, `allowedMcpServers`, `deniedMcpServers`, `allowManagedMcpServersOnly` | managed-mcp.md |
| Plugin and mod policy | Require, allow, or block plugins, marketplaces, and mods fleet-wide, and fix the mod order. | `enabledPlugins`, `extraKnownMarketplaces`, `strictKnownMarketplaces` (alias `allowedMarketplaces`), `blockedMarketplaces`, `strictPluginOnlyCustomization`, `disableSideloadFlags`; `allowManagedModsOnly` (under `pluginConfigs`), `allowManagedHooksOnly`, `prependPlugins`, `appendPlugins` | plugins/org.md, plugins/mods/admin.md |
| Provider and gateway | Route inference through Bedrock, Vertex, Foundry, Claude Platform on AWS, a self-hosted Claude apps gateway, or an LLM gateway instead of the Anthropic API. | `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, `CLAUDE_CODE_USE_FOUNDRY`, `CLAUDE_CODE_USE_ANTHROPIC_AWS`, `ANTHROPIC_BASE_URL`, `allowedProviders`; `claude gateway` | third-party-integrations.md, gateways.md, llm-gateway.md, env-vars.md |
| Deployment plumbing | Fit Claude Code into a managed environment: credential source, proxies and certificates, a mandated process wrapper, telemetry export or opt-out. | `apiKeyHelper`, `forceLoginMethod`, `forceLoginOrgUUID`, `CLAUDE_CONFIG_DIR`; `HTTPS_PROXY`, `NODE_EXTRA_CA_CERTS`, `CLAUDE_CODE_CLIENT_CERT`; `processWrapper`; `CLAUDE_CODE_ENABLE_TELEMETRY`, `OTEL_*`, `DISABLE_TELEMETRY` | authentication.md, network-config.md, corporate-launcher.md, monitoring-usage.md, data-usage.md |

## Retired

Dropped at the next refresh after the one that added the row.

None.
