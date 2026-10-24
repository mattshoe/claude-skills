# Session defaults

Sets defaults so every new session starts in bypass mode, with Remote Control on, and with no workspace trust prompt:

| Key | Value | Effect |
|---|---|---|
| `permissions.defaultMode` | `"bypassPermissions"` | same as `--dangerously-skip-permissions`, no tool prompts |
| `skipDangerousModePermissionPrompt` | `true` | skips the one-time bypass warning at startup |
| `remoteControlAtStartup` | `true` | Remote Control on for every session |

Plus, for the "Accessing workspace ... Is this a project you created or one you trust?" prompt, which no setting turns off:

| Change | Effect |
|---|---|
| `projects["/"].hasTrustDialogAccepted = true` in `~/.claude.json` | no trust prompt in any folder outside a git repo, home included |
| `claude` shell wrapper in the shell profile | trusts the current git repo right before claude starts, since git repos are trusted by repo root and a parent entry does not cover them |

## 1. Warn first

Before changing anything, tell the user in two lines and wait for a yes:
- Bypass mode runs every tool without asking, including file deletes and shell commands. Deny rules still apply.
- Remote Control lets any device signed in to their claude.ai account drive these sessions.
- No trust prompt means a repo they just cloned runs its own project settings, hooks and MCP servers without asking.

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

## 4. Trust prompt

**`~/.claude.json`** (or `$CLAUDE_CONFIG_DIR/.claude.json` when that is set). Claude Code rewrites this file constantly, so read it, change only what is needed, and write it back in one step right away.
- macOS, Linux, WSL: set `projects["/"].hasTrustDialogAccepted` to `true`, keep every other key.
- Windows: look at how existing `projects` keys are written (drive letter case, `/` or `\`) and add the drive root the same way, e.g. `C:/` and `C:\`, both with `hasTrustDialogAccepted: true`.

**Shell wrapper.** Copy the block from the file next to this skill, exactly, markers included. If the markers are already in the profile, replace what is between them instead of adding a second copy.

| Shell | Profile | Block |
|---|---|---|
| zsh (macOS default) | `~/.zshrc` | `<skill base directory>/trust-wrapper.sh` |
| bash | `~/.bashrc` | `<skill base directory>/trust-wrapper.sh` |
| PowerShell | the path in `$PROFILE` (create it if missing) | `<skill base directory>/trust-wrapper.ps1` |

Find the shell with `echo "$SHELL"`. On Windows use PowerShell's `$PROFILE`, Claude Code's Git Bash is not the user's interactive shell. Fish and cmd are not supported, say so. The POSIX wrapper needs `python3` and skips silently without it. The PowerShell wrapper is untested, after installing it ask the user to open a new PowerShell window in a git repo and run `claude` to confirm no prompt.

To turn this **off**: remove `projects["/"]` (and the Windows drive root keys) from `.claude.json` and delete the marked block from the profile. Trust already given to individual repos stays.

## 5. Tell the user

One or two lines: what changed, the files touched, and that it takes effect in the **next** session, in a **new** terminal tab so the profile reloads. Add any of these that apply:

- **Root or sudo** on macOS or Linux: Claude Code refuses to start in bypass mode as root outside a sandbox.
- **Managed policy**: if `permissions.disableBypassPermissionsMode` is `"disable"` in managed settings, an admin has blocked bypass and this setting does nothing.
- **Remote Control** needs a claude.ai login on Pro, Max, Team or Enterprise. API key logins cannot use it. On Team or Enterprise an Owner has to enable it in admin settings first. It is off if `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` is set.
