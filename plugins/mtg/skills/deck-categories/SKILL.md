---
name: deck-categories
description: Break a Magic&#58; The Gathering Commander deck into its synergy categories and allocate every nonland card to exactly one of Ramp, Draw, Removal, Protection or a synergy category, with agent panels and adversarial review loops. Use whenever the user wants a deck's category breakdown, card allocation, role counts, "how many ramp/draw/removal does this run", or "what are this deck's synergy pieces". Returns a count table and writes a detailed document to ~/Documents/mtg/<deck name>/.
allowed-tools: Bash(sh:*)
---

!`sh "${CLAUDE_SKILL_DIR}/sync.sh" mtg deck-categories "${CLAUDE_SKILL_DIR}"`
