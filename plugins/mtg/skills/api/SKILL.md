---
name: api
description: Read or change the user's Magic&#58; The Gathering collection through the MTG REST API, which is the single source of truth for every card they own and every deck they have built. Use whenever a question or task touches their cards, decks, prices or collection data at all&#58; "what do I own", "how many copies of X", "what can I build", "what is my collection worth", "what is in my Alela deck", "add/remove these cards", "what's unassigned", counting, searching, filtering or reporting on cards, and any script or agent that needs collection data. Also use before touching anything in $MTG_API_REPO. Replaces the retired Google Drive sharded-SQLite pipeline — if a doc or script mentions collection-core.db, shards, query.py, collection.py or mobile-requests, it is describing the old dead system.
allowed-tools: Bash(sh:*)
---

!`sh "${CLAUDE_SKILL_DIR}/sync.sh" mtg api "${CLAUDE_SKILL_DIR}"`
