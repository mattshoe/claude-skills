# New session

Opens a tab in the current terminal window and runs `claude` in it. The tab keeps its shell after claude exits.

```sh
sh "<skill base directory>/new-session.sh" [DIR] [PROMPT]
```

- `DIR` defaults to the current working directory. Pass the directory the user names, or this session's project directory if they say "here".
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

Say in one line that the tab is open and what it was started with. If the script exits 2, the terminal is unsupported, report the `TERM_PROGRAM` it printed. Any other failure, show the error.
