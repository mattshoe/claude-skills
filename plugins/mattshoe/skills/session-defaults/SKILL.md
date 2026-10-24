---
name: session-defaults
description: Make every Claude Code session start in bypass permissions mode (same as --dangerously-skip-permissions), with Remote Control on and no workspace trust prompt, by editing the user's settings, ~/.claude.json and shell profile. Works on macOS, Linux, Windows and WSL. Use only when the user asks to turn these defaults on or off.
disable-model-invocation: true
allowed-tools: Bash(sh:*)
---

!`sh "${CLAUDE_SKILL_DIR}/sync.sh" mattshoe session-defaults "${CLAUDE_SKILL_DIR}"`
