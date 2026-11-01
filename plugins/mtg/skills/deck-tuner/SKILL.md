---
name: deck-tuner
description: Tune an existing Magic&#58; The Gathering Commander deck from the user's collection. Use whenever they want to improve, upgrade, review or analyse a built deck - "what should I cut", "find better draw for X", "swap A for B", "what combos does this deck have", "find infinite loops", "what are the odds I assemble a combo", "review this deck with fresh eyes", "score this deck". Covers card suggestions from Scryfall, swaps written to the collection API, combo and loop hunting with subagents, exact combo odds by turn, and blind reviews. For building a new deck from bulk, see build-deck. For buying the cards, see card-buyer.
allowed-tools: Bash(sh:*)
---

!`sh "${CLAUDE_SKILL_DIR}/sync.sh" mtg deck-tuner "${CLAUDE_SKILL_DIR}"`
