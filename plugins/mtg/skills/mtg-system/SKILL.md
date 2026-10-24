---
name: mtg-system
description: Understand, diagnose and safely modify the machinery behind the user's MTG collection — the Cloudflare Worker, the D1 database, the web frontend, the daily maintenance job and the backups. Use whenever work touches that machinery rather than the cards in it&#58; something is broken, slow or returning the wrong thing; the schema or an endpoint needs changing; a deploy did not land; the nightly job did not run; prices are stale; or a session needs to understand how the pieces fit before changing one. Read this before editing anything in $MTG_API_REPO. For using the API rather than changing it, see mtg-api.
allowed-tools: Bash(sh:*)
---

!`sh "${CLAUDE_SKILL_DIR}/sync.sh" mtg mtg-system "${CLAUDE_SKILL_DIR}"`
