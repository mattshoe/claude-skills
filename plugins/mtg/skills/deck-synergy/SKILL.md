---
name: deck-synergy
description: Graph the synergy of a Magic&#58; The Gathering Commander deck and score it out of 100, where 100 is a near-unbeatable cEDH deck. Use whenever the user wants a deck scored, rated, graded or judged for coherence, wants its synergy web or graph, asks "how good is this deck", "how well does this deck fit together", "score my deck", or wants two decks or a swap compared. Takes a deck from the database or a pasted list, asks the user for the synergy categories, tags every card with what it makes and uses, builds the graph, simulates draws, and writes a report to ~/Documents/mtg/<deck name>/.
allowed-tools: Bash(sh:*)
---

!`sh "${CLAUDE_SKILL_DIR}/sync.sh" mtg deck-synergy "${CLAUDE_SKILL_DIR}"`
