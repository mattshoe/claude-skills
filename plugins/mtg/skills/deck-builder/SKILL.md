---
name: deck-builder
description: Build a new Magic&#58; The Gathering Commander deck around a commander the user names, from their free collection or from any card in the game, inside a budget that counts only cards they'd have to buy. Use whenever the user wants a deck built, "build me a deck around X", "make a Y deck", "what would a Z deck look like on $50". Works out the engine and synergy categories, sets category counts against the deck-architecture baseline, picks cards category by category for cross-category value, sizes the mana base with Karsten's math, audits legality and budget, then writes a plain decklist and a play guide to Google Drive and saves a Fetch list in the user's app. Never adds the deck to the collection database without the user's approval.
allowed-tools: Bash(sh:*)
---

!`sh "${CLAUDE_SKILL_DIR}/sync.sh" mtg deck-builder "${CLAUDE_SKILL_DIR}"`
