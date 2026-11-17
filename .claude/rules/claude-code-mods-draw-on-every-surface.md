---
paths:
  - software/claude-code/plugins/**/hooks/**
  - software/claude-code/plugins/**/themes/**
---

# Mods draw on every surface, not only the terminal

A plugin's hooks module runs in every app that loads the plugin: the terminal (TUI), the desktop app, VS Code and mobile. A `ui.render` hook draws on all of them unless it checks `e.surface` (`terminal`, `desktop`, `vscode` or `mobile`).

Why: the chat bubbles in `my-claude-code-style` used terminal block glyphs (`▗▄▖`) for their frames. The desktop app drew those glyphs as solid black bars, and the bubbles hid the app's own message display.

When you add or change a hook, a theme or anything else that changes the look:

1. Decide which surfaces the change is for, and say so to the user before you write it.
2. If the change depends on the terminal (block or box glyphs, column widths, `e.viewport.columns`, colors chosen for a terminal background), return `next(e)` on every other surface.
3. If the change is for all surfaces, tell the user how it will look in the desktop app too, and what you could not check there.
4. Add a test that mounts the component on each surface and checks the result, as `software/claude-code/plugins/common/my-claude-code-style/hooks/bubble.test.tsx` does.
5. Before you commit a change to a plugin, run its tests, for example `claude plugin test software/claude-code/plugins/common/my-claude-code-style`. No CI or git hook runs them. If a test fails, fix the change before you commit it.
6. Ask the user to look at the change in the desktop app before you call it done.
