# New session

Opens a tab in the current terminal window and runs a named `claude` session in it with Remote Control on (`claude -n NAME --remote-control NAME`). The tab keeps its shell after claude exits.

```sh
sh "<skill base directory>/new-session.sh" DIR NAME [PROMPT]
```

- `DIR` is the directory the user names, or this session's project directory if they say "here". `""` means the current working directory.
- `NAME` is required. It shows in the tab title, the resume picker and the Remote Control session list.
  - Use the name the user gave.
  - If they gave none but the task is clear enough to name, infer a short one, 2 to 4 words, from the task (e.g. "fix login bug", "pokemon deck ideas").
  - If there is no task or it is too vague to name, ask the user for a name before running the script. Do not invent a generic one like "new session".
- `PROMPT` is optional. Use it when the user wants the new session to start on a task. Write the prompt so it stands alone, the new session has none of this conversation.
- Run it once. Do not loop or open several tabs unless asked for several.

## What it detects

| Terminal | How |
|---|---|
| tmux (checked first, inside any terminal) | `tmux new-window` |
| Ghostty, iTerm2 | AppleScript |
| Terminal.app | AppleScript plus a Cmd+T keystroke, needs Accessibility permission for the terminal |
| WezTerm | `wezterm cli spawn` |
| kitty | `kitten @ launch`, needs `allow_remote_control` in kitty.conf |
| Windows Terminal | `wt.exe -w 0 nt` |
| GNOME Terminal, Konsole | `--tab` / `--new-tab` |

On macOS the first run may ask the user to allow automation of the terminal app. Tell them to click OK and run it again.

## After

Say in one line that the tab is open, its name, and what it was started with. Exit 2 means the terminal is unsupported, report the `TERM_PROGRAM` it printed. Exit 3 means the name was missing. Any other failure, show the error.
