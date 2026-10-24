---
name: new-session
description: Open a new tab in the terminal this session runs in and start a fresh, named Claude Code session there with Remote Control on, optionally in another directory or with a starting prompt. Asks for a name when none can be inferred. Supports Ghostty, iTerm2, Terminal.app, tmux, WezTerm, kitty, Windows Terminal, GNOME Terminal and Konsole. Use when the user asks for a new session, a new tab, another claude, or to hand a task to a fresh session.
allowed-tools: Bash(sh:*)
---

!`sh "${CLAUDE_SKILL_DIR}/sync.sh" mattshoe new-session "${CLAUDE_SKILL_DIR}"`
