# Pairing candidates: setup

The `pairing-candidates` skill points here when its check reports a setup error or a missing scope.

## One-time setup

The roster names real colleagues and the channel ID is internal, so both live on this machine only, never in the public dotfiles repo this skill is tracked in:

```bash
mkdir -p ~/.config/dotfiles/pairing-candidates
cp ~/.claude/skills/pairing-candidates/roster.example.txt ~/.config/dotfiles/pairing-candidates/roster.txt
echo C0123456789 > ~/.config/dotfiles/pairing-candidates/channel
```

Then replace the example handles, and the example channel ID with the team channel's ID (Slack: channel details → About, at the bottom).

The Slack MCP cannot read presence, so the script uses its own read-only Slack **user** token.

1. Open https://api.slack.com/apps and select **Create New App → From a manifest**. Choose the Comply365 workspace.
2. Paste `~/.claude/skills/pairing-candidates/slack-app-manifest.yaml`. It asks only for the user scopes `channels:read`, `channels:history`, `users:read`, `users:read.email` and `dnd:read`.
3. Select **Install to Workspace**. If the workspace needs admin approval, request it and wait.
4. Copy the **User OAuth Token** (`xoxp-…`) from **OAuth & Permissions**.
5. Store it in the Keychain from a regular terminal window, never from Claude Code: a `!` command gets no keyboard input and stores an empty password. The command asks for the token twice; paste it at each prompt. It never shows on screen or lands in shell history:

   ```bash
   security add-generic-password -U -a "$USER" -s pairing-candidates-slack-token -w
   ```

To rotate the token, run the same command again (`-U` updates the item).

## Add a scope

If the script reports a missing scope, add it to the existing app:

1. Open https://api.slack.com/apps and select the **Pairing Candidates (read-only)** app.
2. In **OAuth & Permissions → User Token Scopes**, add the scope.
3. Select **Reinstall to Workspace**.
4. Copy the new **User OAuth Token** and store it with the Keychain command above.
