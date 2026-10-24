---
name: mtg-remove-cards
description: Remove Magic&#58; The Gathering cards from the user's collection. Use whenever they sold, traded, lost or gave away cards, or wants to correct a miscount - a text list, a CSV export, a single card name, or "take X out of my collection". Handles quantities, sets, collector numbers and foils, writes to the MTG API. Companion to mtg-add-cards; see mtg-api for the database itself.
allowed-tools: Bash(sh:*)
---

!`sh "${CLAUDE_SKILL_DIR}/sync.sh" mtg mtg-remove-cards "${CLAUDE_SKILL_DIR}"`
