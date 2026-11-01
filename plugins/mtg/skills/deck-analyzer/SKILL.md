---
name: deck-analyzer
description: Analyse an existing Magic&#58; The Gathering Commander deck from the user's collection, read only. Use whenever they want a deck analysed or reviewed - "what combos does this deck have", "find infinite loops", "what are the odds I assemble a combo", "review this deck with fresh eyes", "score this deck", "what's its win rate", "find better draw for X", "what should I cut". Covers the commander engine, card suggestions from Scryfall, combo and loop hunting with subagents, exact combo odds by turn, and blind reviews. Never edits decks or buys cards.
allowed-tools: Bash(sh:*)
---

!`sh "${CLAUDE_SKILL_DIR}/sync.sh" mtg deck-analyzer "${CLAUDE_SKILL_DIR}"`
