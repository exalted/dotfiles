---
name: idea
description: Write an idea for the current project into the user's Obsidian ideas note, without the todo judge. Use for `/idea <text>` only; for anything else about side tasks or ideas, use the todo skill.
argument-hint: "<text>"
---

# idea

The forced route of the `todo` skill: the user has decided this is an idea, not a task.

1. Condense the text to 1 to 3 sentences that will remind the user what it was about.
   Keep their words where they carry the meaning.
2. Show the sentences and ask for a yes. Reword on request.
3. On a yes, run:

   ```
   ~/.claude/skills/todo/scripts/todo.py idea --text "<sentences>"
   ```

   The script appends a dated bullet under the project's `##` section of the note named
   in `~/.config/dotfiles/todo/ideas-note`. Outside a git repository it writes under
   `## General`. If the config file is missing, it says which file to create; tell the
   user and stop.

4. Report the note path and the bullet in one line.

Nothing is listed, promoted or tracked from here. The user reads and moves ideas in
Obsidian.
