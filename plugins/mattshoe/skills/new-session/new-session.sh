#!/bin/sh
# Opens a new tab in the terminal this session runs in and starts a named claude session there with Remote Control on.
# Usage: new-session.sh DIR NAME [PROMPT]. DIR "" means the current directory.
DIR=${1:-$PWD}
NAME=${2:-}
PROMPT=${3:-}
if [ -z "$NAME" ]; then
  echo "new-session: NAME is required" >&2
  exit 3
fi

# Shell-quotes one argument.
q() { printf "'%s'" "$(printf %s "$1" | sed "s/'/'\\\\''/g")"; }

# --remote-control takes an optional value, so always give it the name or it eats the prompt.
CMD="claude -n $(q "$NAME") --remote-control $(q "$NAME")"
[ -n "$PROMPT" ] && CMD="$CMD $(q "$PROMPT")"

if [ -n "${TMUX:-}" ]; then
  exec tmux new-window -c "$DIR" "$CMD; exec \$SHELL"
fi

case "${TERM_PROGRAM:-}" in
  ghostty)
    exec osascript - "$DIR" "$CMD" <<'AS'
on run argv
  tell application "Ghostty"
    set cfg to new surface configuration
    set initial working directory of cfg to item 1 of argv
    set initial input of cfg to (item 2 of argv) & "\n"
    new tab in front window with configuration cfg
  end tell
end run
AS
    ;;
  iTerm.app)
    exec osascript - "cd $(q "$DIR") && $CMD" <<'AS'
on run argv
  tell application "iTerm2"
    tell current window
      create tab with default profile
      tell current session to write text (item 1 of argv)
    end tell
  end tell
end run
AS
    ;;
  Apple_Terminal)
    exec osascript - "cd $(q "$DIR") && $CMD" <<'AS'
on run argv
  tell application "Terminal" to activate
  tell application "System Events" to keystroke "t" using command down
  delay 0.3
  tell application "Terminal" to do script (item 1 of argv) in selected tab of front window
end run
AS
    ;;
  WezTerm)
    exec wezterm cli spawn --cwd "$DIR" -- sh -c "$CMD; exec \${SHELL:-sh}"
    ;;
esac

if [ -n "${KITTY_WINDOW_ID:-}" ]; then
  exec kitten @ launch --type=tab --cwd "$DIR" sh -c "$CMD; exec \${SHELL:-sh}"
fi
if [ -n "${WT_SESSION:-}" ]; then
  # cmd does not understand single quotes, so double-quote each argument instead.
  dq() { printf '"%s"' "$(printf %s "$1" | sed 's/"/\\"/g')"; }
  WCMD="claude -n $(dq "$NAME") --remote-control $(dq "$NAME")"
  [ -n "$PROMPT" ] && WCMD="$WCMD $(dq "$PROMPT")"
  # Stop Git Bash rewriting /k into a Windows path like K:/.
  MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' \
    exec wt.exe -w 0 nt -d "$(cygpath -w "$DIR" 2>/dev/null || echo "$DIR")" cmd /k "$WCMD"
fi
if [ -n "${GNOME_TERMINAL_SCREEN:-}" ]; then
  exec gnome-terminal --tab --working-directory="$DIR" -- sh -c "$CMD; exec \${SHELL:-sh}"
fi
if [ -n "${KONSOLE_DBUS_SERVICE:-}" ]; then
  exec konsole --new-tab --workdir "$DIR" -e sh -c "$CMD; exec \${SHELL:-sh}"
fi

echo "new-session: unsupported terminal (TERM_PROGRAM=${TERM_PROGRAM:-unset}, TERM=${TERM:-unset})" >&2
exit 2
