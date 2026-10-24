# Session defaults

Sets two defaults in the user's Claude Code settings so every new session starts with them:

| Key | Value | Effect |
|---|---|---|
| `permissions.defaultMode` | `"bypassPermissions"` | same as `--dangerously-skip-permissions`, no tool prompts |
| `skipDangerousModePermissionPrompt` | `true` | skips the one-time bypass warning at startup |
| `remoteControlAtStartup` | `true` | Remote Control on for every session |

## 1. Warn first

Before changing anything, tell the user in two lines and wait for a yes:
- Bypass mode runs every tool without asking, including file deletes and shell commands. Deny rules still apply.
- Remote Control lets any device signed in to their claude.ai account drive these sessions.

If they asked to turn the defaults **off**, skip the warning.

## 2. Find the file

User settings only. `defaultMode` set to bypass in project or local settings is ignored.

| OS | Path |
|---|---|
| macOS, Linux, WSL | `~/.claude/settings.json` |
| Windows | `%USERPROFILE%\.claude\settings.json` |

If `CLAUDE_CONFIG_DIR` is set, the file is `$CLAUDE_CONFIG_DIR/settings.json` instead. Check with `echo "$CLAUDE_CONFIG_DIR"` (on Windows Claude Code runs commands in Git Bash, so the same works). Resolve `~` to the real home path before reading.

## 3. Edit it

Use the Read and Edit/Write tools, not a script, so it works the same on every OS.

- If the file does not exist, create it with just the three keys.
- If it exists, read it and **merge**. Keep every other key and every existing `permissions` entry (`allow`, `deny`, `ask`, `additionalDirectories`). Only set `permissions.defaultMode`, `skipDangerousModePermissionPrompt` and `remoteControlAtStartup`.
- If the file is not valid JSON, stop and show the user the parse error. Never overwrite it.
- Read it back after writing and confirm it parses and holds the three values.

To turn the defaults **off**: remove `permissions.defaultMode` (or set `"default"`), and set `remoteControlAtStartup` to `false`. Leave `skipDangerousModePermissionPrompt` alone.

## 4. Tell the user

One or two lines: what changed, the file path, and that it takes effect in the **next** session, so restart Claude Code. Add any of these that apply:

- **Root or sudo** on macOS or Linux: Claude Code refuses to start in bypass mode as root outside a sandbox.
- **Managed policy**: if `permissions.disableBypassPermissionsMode` is `"disable"` in managed settings, an admin has blocked bypass and this setting does nothing.
- **Remote Control** needs a claude.ai login on Pro, Max, Team or Enterprise. API key logins cannot use it. On Team or Enterprise an Owner has to enable it in admin settings first. It is off if `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` is set.
