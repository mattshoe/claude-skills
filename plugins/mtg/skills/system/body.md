# The MTG collection system

One Cloudflare D1 database behind a Worker, with a static frontend on GitHub
Pages. Everything lives in `$MTG_API_REPO`.

```
  phone / browser ──▶ $MTG_WEB_URL ──┐
                      (GitHub Pages)     │
                                         ├──▶ $MTG_API_URL
  agents / curl ─────────────────────────┘         (Cloudflare Worker)
                                                        │
                                                   D1: mtg
                                                        │
                            ┌───────────────────────────┴──────────┐
                     Worker cron 08:10 UTC              local 03:00
                     prune prices · prune logs          prices · tags
                     orphans · search · health          backup to $MTG_BACKUP_DIR
```

## Orient yourself first

```bash
curl -s $MTG_API_URL/schema | head -c 3000
curl -s $MTG_API_URL/maintenance    # what the daily job last did
cd $MTG_API_REPO && npm test
```

Never state a number about the collection from memory or a doc. Query it.

## Layout

| Path | What |
|---|---|
| `src/index.js` | the router, and the logging shell around every request |
| `src/cards.js` | `/cards/add`, `/cards/remove` — the Scryfall enrichment |
| `src/decks.js` | create, replace a list, disassemble |
| `src/query.js` | `/query`, read-only enforcement, statement splitting |
| `src/maintenance.js` | the daily tasks |
| `src/log.js` | request logging, 7-day TTL, credential scrubbing |
| `src/admin.js` | HMAC tokens, no expiry |
| `frontend/` | the site, published as an Actions artifact |
| `scripts/` | backup, price refresh, tag backfill, verify, nightly |
| `test/` | the real Worker in workerd against a real local D1 |

Plain JavaScript ES modules. No TypeScript, no framework, no build step, zero
runtime dependencies. Keep it that way.

## Invariants — breaking any of these corrupts data or silently lies

1. **D1 is the source of truth.** The Google Drive shards are a frozen
   rollback. Never write to them, and never treat them as current.
2. **Collections are per owner and never merged.** A query without
   `WHERE owner = ...` sums two people.
3. **Reads are open; anything that writes needs a token.** `/query` decides by
   parsing the statement, so a write that sneaks past `isReadOnly` is a
   security bug, not a quirk. The `logs` table is gated on reads too, because
   it holds IP addresses.
4. **`GET /query` is read-only forever.** A URL that can delete rows is one
   link preview away from doing it.
5. **Every mutation is one `db.batch`.** Half-applied is not a state worth
   being able to reach.
6. **Bulk is `card_usage.free`, not a table.** Owned minus what decks claim.
7. **Colour identity is stored alphabetically** — `'UW'`, not `'WU'`.
8. **Basic lands and tokens are not tracked.** Deleted on purpose. Nothing
   should reintroduce them.

## Limits that have each caused a real outage

| Limit | Consequence | What was done |
|---|---|---|
| D1 allows **100 bound parameters** per statement | an upload over ~99 cards died with "too many SQL variables" | UUIDs are inlined as literals after validation; user text stays bound |
| D1 rejects a very large statement | `SQLITE_TOOBIG` on seeding | byte-aware batching, ~80 KB per statement |
| `Date.now()` barely advances between I/O in Workers | a clock-based throttle collapsed to zero and got 429ed | `src/throttle.js` sleeps unconditionally |
| Scryfall rate-limits Cloudflare's shared egress IPs | price refresh died at ~20 batches | prices run on the Mac from the local bulk file |
| `wrangler d1 export` takes the database offline | a ten-minute outage every night | `scripts/backup.py` pages out through `/query` instead |
| Pages serves everything `max-age=600` | a deploy took ten minutes to land, and could arrive half old | the deploy stamps an import map with the commit — see below |

## Deploying

```bash
npx wrangler deploy      # the Worker, immediate
git push                 # the frontend, via GitHub Actions
```

The Pages workflow runs `scripts/stamp_assets.py`, which rewrites the import
map in `index.html` so every module URL carries `?v=<commit>`. **Do not remove
that.** Without it, Pages' ten-minute cache means an open browser keeps the old
JavaScript, and because each file expires on its own clock it can end up
running a new `index.html` against an old `search.js`.

To see a deploy immediately, load `$MTG_WEB_URL/?x=1` — any query
string is a different URL, so the cache does not apply.

## Testing

```bash
npm test          # eslint over frontend/js, then the full suite
npm run lint
```

The suite runs the actual Worker inside workerd against a real local D1 with
per-test isolated storage, so these exercise real SQLite rather than mocks of
it. Scryfall is stubbed from recorded responses in `test/fixtures/scryfall/`
and **no test can hit the network**: `call()` defaults its stub, so forgetting
one is no longer possible. It used to hand the Worker the real `fetch`, which
made those tests pass or fail on whether the machine was online and, on
timeout, took the pool's isolated storage down and failed unrelated suites.

The stub knows a small fixed set of cards. A test that has to resolve one must
use a card the stub knows, or a card the fixture already owns so nothing is
resolved — otherwise record the card into
`test/fixtures/scryfall/collection-decks.json` and add it there.

`eslint` is there for one reason: `node --check` cannot see a missing import,
and a missing import has taken a page out twice. Keep `no-undef` on.

## Common maintenance

**Schema change.** Edit `schema.sql`, then apply the same change to the live
database with `npx wrangler d1 execute mtg --remote --command "ALTER TABLE ..."`.
The two are not linked — `schema.sql` is what a restored backup builds from, so
a change made in only one place is a backup that restores to the wrong shape.
Backfill existing rows in the same session.

**Run a maintenance task by hand:**

```bash
curl -s -X POST .../maintenance -H "authorization: Bearer $TOKEN" \
  -d '{"only":"orphans","wait":true}'
```

`only` takes one task name, not an array: `prices`, `prune-prices`,
`prune-logs`, `orphans`, `search`, `health`.

**Backups.** `python3 scripts/backup.py` pages the whole database out to a
verified `.sql.gz` in `$MTG_BACKUP_DIR` and proves it restores into plain SQLite
before declaring success. It needs `MTG_ADMIN_PASSWORD` for the `logs` table
and skips that table without it. D1 Time Travel covers the last 30 days
independently.

**Check the logs when something looks wrong:**

```bash
curl -s "$MTG_API_URL/logs?status=error&since=24" \
  -H "authorization: Bearer $TOKEN"
```

Logging never blocks a request — it happens in `ctx.waitUntil` after the
response — and every failure in it is swallowed. A log that breaks the thing it
logs is worse than no log.

## Cautions

- **Never commit with `git add -A`** in this repo without reading the staged
  list. A `frontend/CNAME` swept in that way once claimed the domain and 301ed
  the live site into a name that did not resolve yet. Stage by name.
- **A cached 301 is keyed by URL**, so a redirect mistake survives a hard
  refresh. Add a query string to get past it.
- `~/.mtg-api.env` holds the Cloudflare token, the admin password and the
  config vars listed in the api skill. `chmod 600`, never committed.
- The Drive folder's `deckpool.py` / `deckcheck.py` / `deckchart.py` read the
  frozen shards, so their pool is stale. Do not use them to decide what the user
  owns.

## Related skills

**api** is how to use the API — read that first for the data shape and the
query gotchas. `add-cards` / `remove-cards` edit the collection.
`build-deck` builds a deck from unassigned cards. This skill is the
machinery underneath them.
