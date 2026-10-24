---
name: mtg-api
description: Read or change the user's Magic&#58; The Gathering collection through the MTG REST API, which is the single source of truth for every card they own and every deck they have built. Use whenever a question or task touches their cards, decks, prices or collection data at all&#58; "what do I own", "how many copies of X", "what can I build", "what is my collection worth", "what is in my Alela deck", "add/remove these cards", "what's unassigned", counting, searching, filtering or reporting on cards, and any script or agent that needs collection data. Also use before touching anything in $MTG_API_REPO. Replaces the retired Google Drive sharded-SQLite pipeline — if a doc or script mentions collection-core.db, shards, query.py, collection.py or mobile-requests, it is describing the old dead system.
---

# The MTG collection API

One Cloudflare D1 database behind a REST API. It is **the** collection — not a
copy of one, not a cache in front of one.

| | |
|---|---|
| API | `$MTG_API_URL` |
| Web UI | `$MTG_WEB_URL` |
| Code | `$MTG_API_REPO` |
| Backups | ``$MTG_BACKUP_DIR``, nightly, plus D1 Time Travel for 30 days |

Reads are open. Anything that writes needs an admin token.

## Config

Nothing about a deployment is hardcoded. Every skill reads it from
`~/.mtg-api.env`, loaded with `set -a; . ~/.mtg-api.env; set +a`:

| Var | What |
|---|---|
| `MTG_API_URL` | the Worker, no trailing slash |
| `MTG_WEB_URL` | the web UI |
| `MTG_OWNER` | your owner name in `cards.owner` |
| `MTG_OWNER_ID` | your owner id in `card_usage.owner_id` |
| `MTG_ADMIN_PASSWORD` | mints write tokens, never commit it |
| `MTG_API_REPO` | local checkout of the API code |
| `MTG_BACKUP_DIR` | where backups land |

If the file or a var is missing, stop and ask for it. Never guess a URL.
Keep the file `chmod 600`.

## Start here, every time

```bash
curl -s $MTG_API_URL/schema | head -c 3000
```

That returns every table and view with its columns, row counts and the join
keys. **Never state a number about the collection from memory or from a
document — query it.** Counts change daily and a stale number in a doc gets
believed.

## Reading: `POST /query`

Arbitrary read-only SQL. One statement per call.

```bash
curl -s -X POST $MTG_API_URL/query \
  -H 'content-type: application/json' \
  -d '{"sql":"SELECT name, qty FROM cards WHERE owner = ? AND cmc <= 2 LIMIT 20","params":["$MTG_OWNER"],"fmt":"objects"}'
```

- `fmt`: `rows` (default — `cols` once, rows as arrays, cheapest to read),
  `objects`, or `tsv`.
- `limit` caps the result, default 5000.
- `GET /query?sql=...` exists for callers that can only fetch a URL. It is
  **read-only by design**; POST is not restricted.
- Errors come back as `{"error":"near \"SELEC\": syntax error"}` with a 400.

Set a real `User-Agent`. Cloudflare answers some default agents with a 403.

## Writing

Every write needs a bearer token. Get one with the password in
`~/.mtg-api.env`:

```bash
set -a; . ~/.mtg-api.env; set +a
TOKEN=$(curl -s -X POST $MTG_API_URL/admin \
  -H 'content-type: application/json' \
  -d "{\"password\":\"$MTG_ADMIN_PASSWORD\"}" | python3 -c 'import json,sys;print(json.load(sys.stdin)["token"])')
```

Tokens do not expire — rotating `ADMIN_PASSWORD` is what revokes them.
Then send `-H "authorization: Bearer $TOKEN"`.

**Always dry-run first.** Every write endpoint takes `"dry_run": true`, returns
exactly what it would do, and writes nothing. Show the user that before applying.

| Endpoint | What it does |
|---|---|
| `POST /cards/add` | `{owner, list, dry_run}` — a decklist in, cards added |
| `POST /cards/remove` | same shape, cards taken out |
| `POST /decks/create` | a new deck from the wizard: `{name, format, owner, commander, bracket, list}` |
| `POST /decks/list` | `{slug, commander, list}` — replaces a deck's list wholesale |
| `POST /decks/disassemble` | `{slug}` — deletes the deck, its cards go back to bulk |
| `GET /decks/formats` | the formats a deck can be |
| `POST /query` | a write statement also works here, and is also gated |
| `GET|POST /maintenance` | the daily job; `{"only":"orphans","wait":true}` |
| `GET /logs`, `GET /logs/stats` | the request log — admin, because it holds IPs |

`list` takes whatever an exporter produces — bare names, `4 Sol Ring`,
`1 Sol Ring (M3C) 409 *F*`, Archidekt categories, MTGO `SB:` prefixes, section
headings, and CSV from ManaBox / Moxfield / Deckbox. Format is detected, not
declared. A set code plus collector number pins an exact printing and **wins
over the name**, so check the preview: `1 Sol Ring (M3C) 409` resolves to
whatever M3C 409 actually is.

## The shape of the data

One row in `cards` per **(owner, printing, finish)**, with `qty` for how many of
that stack they have. So "how many Sol Rings" is `SUM(qty)`, never `COUNT(*)`.

Join keys:
- `cards.name_norm` = `lower(trim(name))`. `deck_cards.name_norm` and
  `totals.name_norm` match it.
- `cards.id` ← every `card_*.card_id`.
- `cards.oracle_id` ← `legalities`, `rulings`.

Useful views: `totals` (per owner+name), `card_usage` (owned / in_decks /
**free**), `bulk_cards` (`card_usage` where free > 0), `deck_gaps`,
`deck_conflicts`, `decks_not_built`, `card_prices`.

**Bulk is not a table.** It is `card_usage.free` — owned minus what decks have
claimed. Nothing moves a card "into bulk"; a deck letting go of it is what makes
it free.

## Gotchas that have each caused a real bug

- **Owner.** A database can hold several owners and the collections are never
  merged. A query without `WHERE owner = ...` silently sums two people.
- **Colour identity is stored alphabetically.** Azorius is `'UW'`, not `'WU'`;
  Golgari is `'BG'`. Sort the letters before comparing, or exact-match returns
  nothing.
- **Absence in `legalities` means not legal.** Only legal/banned/restricted are
  stored. Use `NOT EXISTS`; treat NULL as illegal, not unknown.
- **FTS**: `SELECT ... FROM card_search WHERE card_search MATCH 'proliferate'`.
  `card_search.rowid` = `cards.id`. Hyphenated tag slugs need double quotes —
  `-` is an FTS operator.
- **Basic lands and tokens are not tracked at all.** They were deliberately
  deleted from `cards`. A deck listing 20 Forests is not short 20 cards, and
  nothing will buy them.
- **D1 caps a statement at 100 bound parameters.** Chunk, or inline values you
  have validated.
- **Grouping fans out across printings.** `GROUP BY owner, name_norm` and take
  `MIN(id)` for a representative row.
- **`deck_cards` dedupes by name with `qty`** — always `SUM(qty)`.

## Editing a deck moves real cards

`POST /decks/list` and `POST /decks/create` reconcile the collection with the
list. Cards the deck drops go back to bulk; cards it gains come out of bulk;
and **anything bulk cannot cover is bought** — it goes through `/cards/add`
with full Scryfall enrichment so a real row exists. The reply carries
`returned` and `acquired`, and a dry run shows the shopping list first.

Proxy and PROPOSED decks buy nothing, because `card_usage` does not count them
as consuming anything.

## Maintenance and backups

A Worker cron runs daily at 08:10 UTC: prune prices, prune logs (7-day TTL),
sweep orphans, repair the search index, health check. Prices, tag backfill and
the backup run on the Mac at 03:00 (`scripts/nightly.sh`), because Scryfall rate-limits Cloudflare's shared egress
IPs after about twenty batches.

`python3 scripts/backup.py` writes a verified `.sql.gz` that restores into
plain SQLite. Run it before anything destructive.

## Working on the code

`$MTG_API_REPO`. Plain JavaScript ES modules, no framework, no build step.
`src/` is the Worker, `frontend/` is the site, `test/` runs the real Worker
against a real local D1 in workerd.

```bash
npm test          # eslint + the full suite, no network
npx wrangler deploy
```

The frontend deploys itself from `main` via GitHub Actions. Pages serves
everything with `max-age=600`, so the deploy stamps an import map with the
commit — do not remove that, or an edit takes ten minutes to reach a browser
and can arrive half-applied.

## The old system is gone

The Google Drive pipeline — five `collection-*.db` shards, `collection.py`,
`query.py`, `build_collection_db.py`, the `mobile-requests/` queue — is a
**frozen rollback**. Read it if you must; never write to it. Anything it says
about the collection is a snapshot from before the migration.

That folder's own `deckpool.py`, `deckcheck.py` and `deckchart.py` read those
shards, so their card pool is frozen too. Their scoring logic is still worth
reading; their data is not.
