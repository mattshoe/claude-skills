---
name: mtg-build-deck
description: Build a Magic&#58; The Gathering Commander deck for the user out of the cards they own but has not committed to a deck. Use whenever they want a new deck, a deck around a particular commander or theme, or asks what they could build from their bulk - "build me a deck", "what can I make with my spare cards", "make something around +1/+1 counters". Runs an iterative build-grade-revise loop with independent grader panels at every step and writes the finished decklist to notes/. Companion to mtg-add-cards and mtg-remove-cards.
allowed-tools: Bash(sh:*)
---

!`sh "${CLAUDE_SKILL_DIR}/sync.sh" mtg mtg-build-deck "${CLAUDE_SKILL_DIR}"`
