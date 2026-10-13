---
name: comply365-recap
description: Scheduled job only, started by the recap launch agent on weekdays at 07:47 and after login. Writes an unread Obsidian note that explains, in plain language, the work delivered to main across the team's GitLab projects since the last recap, tied together across projects and matched with Jira stories and team Slack threads. Do not invoke it in an interactive session.
user-invocable: false
---

# Recap

Tell the user, in plain language, what the team delivered since the last recap: what is new, what is better, what is fixed, and where the products are heading. Every item also gets the technical explanation, folded, for when the user wants to read more.

The projects are parts of one product: a backend, the customer web app and an internal admin console. One feature often touches two or three of them. **The recap tells what happened to the product, not what happened in each project.** Never structure it per project, and never split one piece of work into one item per project.

The result is one Obsidian note per run, called a recap, in the configured vault folder, with the property `read: false`. The folder's Base (`<folder>.base`) lists the unread notes, and the user ticks `read` there. When recaps pile up unread, a catch-up note sums them up (step 7). The note format lives in `scripts/note.py`, so every note has the same properties and layout.

This skill runs only unattended, from `software/claude-code/comply365-recap.sh` in the dotfiles repo, and nobody can answer a question:

- Never ask one. Do not `cd`. Run every script with the exact command shown here, because the run pre-allows only those.
- It needs no local clone: commits come from the GitLab API. The run files go into `$PWD/.claude/scratchpad.local/recap/<date>/`.
- **This skill only reads,** except for its note. Never transition or comment on a Jira issue, react to or post a Slack message, or change other notes in the vault.
- If a step cannot continue (a setup error, a GitLab error, an expired Jira or Slack sign-in, a missing tool), write the failure note and stop. Do not work around a broken source, and do not write a recap with a source silently missing. There is only ever one failure note: a new failure updates it and keeps the day failures started. Nothing is lost, because the next successful run covers everything since the last recap:

  ```bash
  uv run --quiet --no-project --script ~/.claude/skills/comply365-recap/scripts/note.py --error "<what failed, and the one action that fixes it>"
  ```

## 1. Collect the commits

```bash
uv run --quiet --no-project --script ~/.claude/skills/comply365-recap/scripts/collect.py
```

It reads, through the GitLab REST API, the commits that reached `main` in the window for each project in `~/.config/dotfiles/recap/projects.txt`. It then writes `collected.json` into the work dir it prints: the window, the Jira browse URL and project key, the team channel, and per project the commits (subject, body, author, files with line counts, story keys, commit URL). Merge commits are left out.

**Window:** it starts where the newest earlier recap ends (its `window_end`), however long ago: after a holiday with the Mac off, the first run covers the whole absence. Usually that is 07:45 on the previous workday, and Monday covers the weekend. It ends now. `collected.json` lists the `workdays` the window covers.

The API, not `git fetch`, is the source on purpose: GitLab refuses git access once the group's SAML SSO session expires, which it usually has by the morning, but a token keeps working.

- **Exit 2, `SETUP ERROR`:** write the failure note with the message and stop. A refused token (401/403) is one: it expired or was revoked.
- **Exit 3, `GITLAB ERROR`:** GitLab is unreachable or answered with an error. Write the failure note and stop.
- **Zero commits in every project:** still continue. The recap then says nothing reached main, and covers only **Coming up**.

Read `collected.json` in full before the next step.

## 2. Read Jira

Use the Atlassian MCP. Get the `cloudId` once with `getAccessibleAtlassianResources`.

1. **Delivered stories:** one `searchJiraIssuesUsingJql` for `key in (<story_keys>)` with the fields `summary`, `status`, `issuetype`, `parent`, `description`. The description and the parent epic tell you what the story is for, in the words the team uses, and which stories belong to the same feature.
2. **Direction:** `project = <KEY> AND sprint in openSprints() AND statusCategory != Done ORDER BY rank`, plus `project = <KEY> AND created >= "<window start, yyyy-MM-dd HH:mm>"`. Fetch summaries, status and parent only, and at most 40 issues.

## 3. Read Slack

Use the Slack MCP, read tools only.

1. `slack_read_channel` on the team channel from `collected.json`, with `oldest` = the window start as a Unix timestamp. Open threads with replies (`slack_read_thread`) only when they discuss a delivered change, a release, an incident or a plan.
2. For each delivered story key with little context so far, `slack_search_public` for `<KEY>-<n> after:<window start date minus 7 days>`. Search at most 10 keys.

On a long window (more than 3 workdays), read at most the newest 300 channel messages, and open only threads about releases, incidents, plans, or the biggest pieces of work.

Use Slack for the why (who asked for the change, what problem it solves), for release and incident news, for plans, and to see which changes in different projects belong together. Link a thread only when it adds to an item. Never quote private conversations, and never put personal data in the recap.

## 4. Find what belongs together

Before you write anything, group the commits of all projects into pieces of work. Commits belong to the same piece of work when any of these is true:

- They share a story key, or their stories share a parent epic.
- One side provides what the other uses: a backend endpoint, field, permission, event or setting that a web app or console commit starts to call, show or send. Compare names in subjects, bodies and file paths (a `serviceAccess` route and a `service-access` page, an `include_system_users` flag and a "system users" toggle).
- The same Slack thread or Jira story discusses both.
- A commit without a story key (`[NO-ID]`) follows up on, or prepares for, another piece of work in the same window.

When a link is still unclear, read the diffs with the GitLab MCP: `get_commit` with the commit `url` from `collected.json`, `include: ["diff"]` and `diff_detail: "full_patch"`. Read only what you need. A big diff does not mean an important change. Tie commits together only on evidence. Unrelated work in the same area stays separate.

## 5. Write `recap.json`

Write `<work dir>/recap.json`:

```json
{
  "headline": "One sentence that names the most important change",
  "summary": "Two to four sentences: the shape of the day for a reader who reads nothing else.",
  "items": [
    {
      "kind": "new | improved | fixed | under_the_hood",
      "title": "What changed, in user terms",
      "summary": "One or two sentences: what it does and who it helps.",
      "details": "Technical explanation in Markdown.",
      "diagram": "Optional Mermaid source, without the ``` fence.",
      "jira": ["KEY-123"],
      "slack": [{"label": "Release thread", "url": "https://…"}],
      "commits": ["<short sha>", "…"]
    }
  ],
  "heading_next": [
    {"title": "…", "summary": "…", "jira": ["KEY-456"], "slack": []}
  ],
  "jira_issues": {"KEY-123": {"title": "…", "status": "…", "type": "Story"}},
  "minor_commits": ["<short sha>"],
  "notes": ["Only real gaps, e.g. 'Slack search returned nothing for KEY-641.'"]
}
```

**Long window (more than 3 workdays):** the reader was away, so write for someone catching up. The `headline` and `summary` tell what is different in the product now. Group more coarsely: one item per feature or epic, even when it holds many commits, and put follow-up fixes to a feature into that feature's item. Mention in the summary that the recap covers several days.

**Items:** one item per piece of work from step 4, with the commits of every project it touches. Every commit is in exactly one item or in `minor_commits`. `minor_commits` is only for changes a reader gains nothing from (removed console logs, a typo, a lint fix). Order the items in each kind by importance to users. The note shows the products of each item from its commits, so do not repeat project names in the title.

**Kinds:**

- `new`: something a user can do or see that did not exist before.
- `improved`: an existing feature works better, faster or more clearly.
- `fixed`: something that was wrong now works as it should.
- `under_the_hood`: changes users do not see: infrastructure, tooling, tests, refactors, security hardening, data migrations, model changes. Say why each one matters.

**Writing:** the user reads the top of the note over coffee and should get the day at a glance. Write the headline, summaries and titles the way a teammate would tell them in the hallway: warm, plain and concrete. Everything technical goes into `details`.

- Say what someone can now do, see or stop worrying about, and who that someone is (analysts, airlines, support staff, the team). Not what the code does.
- Use everyday words. Keep the product's own terms the team uses (operational area, investigation, Cockpit), but no engineering words: no endpoint, flag, scope, mapping, migration, allowlist, refactor, enforce, ensure, leverage, functionality.
- Short sentences, but let them flow like speech. Contractions are fine ("can't", "it's"). Never stack nouns ("operational area mapping enforcement").
- A title is something a person would say, at most about ten words: "Pick a whole aircraft family in one click", not "Nested, searchable filters for aircraft models".
- A summary is one or two sentences: the change, then why it matters. Add a small concrete example when it helps ("tick A320 family to get every A320 variant").
- For a fix, say what went wrong before in one plain clause ("Before this, other users could send them too").
- State only facts that the commits, Jira or Slack show; do not guess at intent or invent benefits.

| Robot-like | Human |
|---|---|
| Enforce operational area mapping for imported reports | Every report now has an area, so access rules always apply |
| The fishbone service now applies the caller's access scope | Root-cause analysis only uses reports you're allowed to see |
| Each report has exactly one embedding | "Similar reports" won't show the same report twice |

- **`headline` and `summary`** describe the day as product themes, never as a list of projects ("Filters are easier to use, and three security gaps are closed", not "The backend got 9 commits and the console got 4").
- **An item that spans projects** tells one story from end to end: what people see, and what changed behind it so that it works ("Support staff can now include system users in an investigation. Cockpit has a new switch for it, and the backend checks who may use it."). Its `details` follow the same path, one part after the other (backend, then web app or console), and say how the parts connect: the endpoint, field or event between them.
- **Work that is not finished on all sides:** when only one side of a feature shipped (a backend endpoint that nothing calls yet, a screen that waits for its backend), say so plainly, and name the missing side if Jira or Slack shows it.

**Diagrams:** add a `diagram` only when a picture explains the change faster than words. A change that crosses projects is the best case: draw the path from the user's screen to the backend and back, with the changed parts marked. Other good cases: a changed data flow, a before/after of a process, a state machine. Use Mermaid (`flowchart LR`, `sequenceDiagram`, `stateDiagram-v2`), at most about 10 nodes, with labels in plain words and product names, not project names. Most items need none. Never draw a diagram that only repeats the text.

**`heading_next`** (shown as **Coming up**): two to five entries about where the products are going, in the same voice, from open-sprint stories in progress, new stories and Slack plans. Prefer themes that cross products over single tickets ("The investigation console is getting access controls", with its stories in `jira`).

`jira_issues` holds every key you put in any `jira` list, with its summary as `title`, so the note can show its status.

## 6. Write the note

```bash
uv run --quiet --no-project --script ~/.claude/skills/comply365-recap/scripts/note.py --work-dir <work dir>
```

It writes `<vault folder>/<YYYY-MM-DD> (<Mon> <D>) Recap.md` and prints its path. The note is named after the workdays it covers, not the day it was written: Tuesday's run writes `2026-10-12 (Oct 12) Recap.md`, a Monday run is named after Friday, and a long window gets a range (`2026-10-01 (Oct 1–14) Recap.md`). A rerun on the same morning replaces that note, which resets it to unread. A successful run also moves the failure note to the Trash. It creates the folder's Base on the first run and never changes it afterwards.

**Exit 4, `INVALID`:** fix `recap.json` as listed (usually a commit missing from every item) and run it again. Do not edit the note by hand: the format lives in `note.py`.

## 7. Write the catch-up note, when due

```bash
uv run --quiet --no-project --script ~/.claude/skills/comply365-recap/scripts/note.py --unread
```

It prints the unread recaps and `catch_up_due`. That is true when 3 or more recaps are unread and no unread catch-up note covers exactly them. Otherwise skip to step 8.

When it is due:

1. Read every unread recap note it lists (the `path`).
2. Get the current Jira status of their stories with one `searchJiraIssuesUsingJql` (`key in (…)`, fields `summary`, `status`), so the catch-up can say what has shipped since.
3. Write `<work dir>/catch-up.json`:

   ```json
   {
     "headline": "One sentence: the biggest change while the user was away",
     "summary": "Two to four sentences on what is different in the product now.",
     "themes": [
       {"title": "…", "summary": "…", "jira": ["KEY-123"], "recaps": ["<recap note name>", "…"]}
     ],
     "jira_issues": {"KEY-123": {"title": "…", "status": "…", "type": "Story"}}
   }
   ```

   Three to seven themes across all the recaps, in the same voice as a recap. A theme joins the work of several days into one story ("Filters got a full redesign over the week"). In its summary, say what happened since, when Jira shows it ("now live", "still being tested"). `recaps` names the recap notes the theme comes from, exactly as `--unread` printed them.
4. Run:

   ```bash
   uv run --quiet --no-project --script ~/.claude/skills/comply365-recap/scripts/note.py --catch-up <work dir>
   ```

   It writes `<YYYY-MM-DD> (<range>) Catch-up.md` over all unread recaps, and replaces an older unread catch-up note. **Exit 4:** fix `catch-up.json` as listed and run it again.

## 8. Finish

Move the work dir to the Trash (`trash <work dir>`) and print the note paths. After a failure, keep the work dir for debugging, and print where it is.

## The note

- **Properties:** only `read` (checkbox, `false` when written), `headline` (the Base shows it), and `window_end` (where the next run starts). Everything else is in the file name or the text.
- **Body:** the headline and the summary, links to each kind section, then one section per kind. Each item has its title, the products it touches, Jira and Slack links, its plain summary, and a folded `> [!info]- Technical details` callout with the details, the diagram and the commit table across all its projects. Then **Coming up**, the sources per project, and a `Related:` line to the previous recap and the Base.
- **Catch-up note:** `<YYYY-MM-DD> (<range>) Catch-up.md`, with the themes, links to every recap it covers, and the property `covers` (their names). When the user ticks it read, the next start (07:47, wake or login) marks those recaps read too and removes `covers` (`scripts/prepare.py`), so a recap unticked later stays unread. An unread catch-up note that covers fewer than 3 unread recaps goes to the Trash.
- **Failure note:** `<YYYY-MM-DD> (<Mon> <D>) Recap failed.md`, only one, named after the first workday that failed, headline "Recaps missing since <that day>", with the latest error. Unread again after each failure.
- **Base:** `<folder>/<folder>.base`, over every note in the folder. **Unread** shows a catch-up note first, then a failure note, then the recaps, newest first (a formula on the file name); **All** shows every note, newest first. The user can change its views in Obsidian; the skill never overwrites it.

## Schedule

`software/claude-code/comply365-recap.sh` (installed as `~/.claude/recap.sh`) is the launch agent `com.dotfiles.comply365-recap`, work profile only. It starts at 07:47 Monday to Friday, on wake when the Mac slept through 07:47, and at every login. Each start first runs `scripts/prepare.py`, which applies catch-up read ticks and then stops the start on a weekend or when today's recap is already written, so restarts never write a second recap. Otherwise it runs `claude -p` on the most capable model (`--model fable --effort xhigh`) with a prompt that invokes this skill, from `~/.local/state/recap`, with exactly the tools above pre-allowed. If `claude` itself fails, it writes the failure note, which points to `~/Library/Logs/recap.log`. It writes files only; it never drives the Obsidian app.

- Run it now: `/bin/launchctl kickstart "gui/$(id -u)/com.dotfiles.comply365-recap"`.
- Mac off or asleep for days: the first start afterwards covers the whole gap in one recap.
- Mac on while the user is away: a recap per workday, then a catch-up note once 3 or more are unread.

## Configuration

All internal values live on this machine only, never in the public dotfiles repo this skill is tracked in.

- `~/.config/dotfiles/recap/projects.txt`: the GitLab projects, as `<project URL> | <product name>` per line (see `projects.example.txt`). The branch is `BRANCH` in `scripts/collect.py`.
- `~/.config/dotfiles/recap/channel`: the team channel ID (`C…`).
- `~/.config/dotfiles/recap/vault-folder`: the absolute path of the vault folder for the notes. It must be inside an Obsidian vault.
- `~/.config/dotfiles/jira`: the Jira browse URL prefix `https://<site>/browse/<KEY>-`, shared with the `jira` command. Its key is the project the commits are matched with.
- Keychain item `recap-gitlab-token`: a GitLab personal access token with only the `read_api` scope.
- `WINDOW_ANCHOR` in `scripts/collect.py`: the usual window boundary (07:45). `CATCH_UP_THRESHOLD` in `scripts/common.py`: the unread recaps that make a catch-up note (3).

## One-time setup

1. Create the config files above (`mkdir -p ~/.config/dotfiles/recap`).
2. Create the GitLab token: GitLab → avatar → **Edit profile → Access tokens → Add new token**. Name it `recap`, set the longest expiry allowed, and select only `read_api`. Store it in the Keychain (it asks for the token, so the token never lands in shell history):

   ```bash
   security add-generic-password -U -a "$USER" -s recap-gitlab-token -w
   ```

   When it expires, the day's note is a failure note that says so. Create a new token and run the same command (`-U` updates the item).
3. Install the schedule: run `software/claude-code/claude-code.rb` in the dotfiles repo.
