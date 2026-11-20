---
name: deck-architecture
description: The user's deck architecture for Magic&#58; The Gathering Commander decks, meaning the categories every deck is built from, the baseline count for each, when to move those counts, and the rule that most cards should fill 2 or more categories. Load it before making any judgment about a deck or a card in a deck&#58; suggesting adds or cuts, rating a card or a deck, reviewing, building, swapping, upgrading, comparing, "is this deck good", "what's weak here", "what should I add", and anything else that weighs a deck. Knowledge only, no workflow. Category counts are only one use of it.
allowed-tools: Bash(sh:*)
---

!`sh "${CLAUDE_SKILL_DIR}/sync.sh" mtg deck-architecture "${CLAUDE_SKILL_DIR}"`
