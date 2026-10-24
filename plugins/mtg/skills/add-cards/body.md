# Adding cards to the collection

The collection lives behind the REST API at
`$MTG_API_URL`. It is the single source of truth.
See the **api** skill for the database shape and query rules.

Adding needs an admin token. Get one from the password in `~/.mtg-api.env` (see Config in the api skill):

```bash
set -a; . ~/.mtg-api.env; set +a
TOKEN=$(curl -s -X POST $MTG_API_URL/admin \
  -H 'content-type: application/json' \
  -d "{\"password\":\"$MTG_ADMIN_PASSWORD\"}" | python3 -c 'import json,sys;print(json.load(sys.stdin)["token"])')
```

## Procedure

**1. Dry run first — always.** Never send `dry_run: false` on the first call.

```bash
curl -s -X POST $MTG_API_URL/cards/add \
  -H 'content-type: application/json' -H "authorization: Bearer $TOKEN" \
  -H 'user-agent: mtg-cli/1.0' \
  -d '{"owner":"$MTG_OWNER","dry_run":true,"list":"4 Lightning Bolt (2X2) 117\n2x Counterspell"}'
```

For a long list, build the JSON with a script rather than escaping newlines by
hand:

```bash
python3 -c '
import json,os,sys
print(json.dumps({"owner":"$MTG_OWNER","dry_run":True,"list":open(sys.argv[1]).read()}))
' /path/to/list.txt > /tmp/body.json
curl -s -X POST .../cards/add -H "authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' -d @/tmp/body.json
```

**2. Show them the plan.** The reply is:

```json
{"applied": false, "resolved": 2, "failed": 0,
 "changes": [["Lightning Bolt","2X2","117","nonfoil",0,4]],
 "errors": [], "notes": []}
```

Each `changes` row is `[name, set, collector_number, finish, qty_before,
qty_after]`. Surface, rather than burying:

- **A resolved name that differs from what they typed.** Set plus collector
  number **wins over the name** — `1 Sol Ring (M3C) 409` resolves to whatever
  M3C 409 actually is, which is not Sol Ring. This is the single most common
  way a list goes in wrong.
- Anything in `errors` — those lines are skipped entirely, the rest still
  apply.
- Anything in `notes` — not failures, usually enrichment skipped on a big
  import.

**3. Apply once they confirm.** Same body with `"dry_run": false`, then report
the new totals by querying, not from memory.

## Which owner

Always send `owner` explicitly, `$MTG_OWNER` unless told otherwise. If the
database holds more than one owner and there is any doubt whose cards these
are, ask. Collections are never merged and there is no cheap undo.

## Input formats

| Input | Meaning |
|---|---|
| `4 Lightning Bolt (2X2) 117 *F*` | qty, name, set, collector number, foil |
| `4 Lightning Bolt (2X2)` | resolves the collector number |
| `2x Counterspell` / `2 Counterspell` | qty + name |
| `Sol Ring` | bare name, qty 1 |
| `1 Ygra, Eater of All (BLB) 294 foil` | `foil` / `etched` work like `*F*` / `*E*` |

Also handled without being told: Archidekt `[Category]` suffixes, MTGO `SB:`
prefixes, `Deck` / `Sideboard` / `Commander` headings, `#` and `//` comments,
and CSV from ManaBox, Moxfield or Deckbox — columns are matched by name, so
their order does not matter. Paste the file whole.

Without a set code, Scryfall picks the most recent paper printing.

## What it writes

One `cards` row per (owner, printing, finish); an existing stack increments
rather than duplicating. Child rows — colours, types, keywords, finishes,
games, legalities, the FTS row — are derived from the Scryfall response, and a
genuinely new oracle id also pulls its rulings. The whole thing is one D1
batch, so a Scryfall failure leaves the database untouched.

Tags are the one gap: they come from Scryfall's Tagger bulk file, which has no
per-card API, so a newly added card has none until the nightly backfill.

## Notes

- Basic lands and tokens are **not tracked** and should not be added. They were
  deliberately removed from the collection.
- Adding more than ~1000 lines at once is refused; split it.
- Web UI alternative: `$MTG_WEB_URL` → Add, which walks list →
  owner → preview → apply and will not let anyone skip the preview.
