# Removing cards from the collection

The collection lives behind the REST API at
`$MTG_API_URL`. It is the single source of truth.
See the **mtg-api** skill for the database shape and query rules.

Removing needs an admin token:

```bash
set -a; . ~/.mtg-api.env; set +a
TOKEN=$(curl -s -X POST $MTG_API_URL/admin \
  -H 'content-type: application/json' \
  -d "{\"password\":\"$MTG_ADMIN_PASSWORD\"}" | python3 -c 'import json,sys;print(json.load(sys.stdin)["token"])')
```

## Procedure

**1. Dry run first — always.** Removal has no undo short of restoring a
backup.

```bash
curl -s -X POST $MTG_API_URL/cards/remove \
  -H 'content-type: application/json' -H "authorization: Bearer $TOKEN" \
  -H 'user-agent: mtg-cli/1.0' \
  -d '{"owner":"$MTG_OWNER","dry_run":true,"list":"1 Sol Ring\n2 Lightning Bolt (2X2) 117"}'
```

**2. Show them the plan.** Each `changes` row is `[name, set,
collector_number, finish, qty_before, qty_after]`. Check especially:

- **Which printing it picked.** Without a set code, copies come out of the
  plainest printing first. If they meant the foil or a specific set, say which
  one the preview chose before applying.
- Anything in `errors` — those lines are skipped, the rest still apply.

**3. Apply once they confirm**, with `"dry_run": false`.

## What it refuses

- **Removing more than they own** is refused outright and changes nothing. It
  does not remove what it can and shrug.
- **Removing a card that is not there** is an error, not a silent no-op.
- Removing a foil never touches the nonfoil, and vice versa.

## What it cleans up

At zero the `cards` row goes, along with every child row — colours, types,
keywords, finishes, games, promo types, frame effects, tags — the FTS row, the
price row and any alias. Oracle-level rows (`legalities`, `rulings`) go only
when no other printing shares that oracle id.

## A card in a deck can still be removed

The deck keeps listing it and it shows up in `deck_gaps` as a card they no
longer has. That is deliberate — the deck is a record of what they built, not a
lock on the collection. **Say so when it happens**, so they can decide whether
the deck list needs editing too:

```sql
SELECT deck, name, qty FROM deck_gaps WHERE owner = '$MTG_OWNER';
```

Note the asymmetry with deck editing: editing a deck's list *buys* what bulk
cannot cover, but removing cards directly does not touch any deck.

## Which owner

Always send `owner` explicitly, `$MTG_OWNER` unless told otherwise. If there is
any doubt whose cards these are, ask.

## Notes

- Input formats are exactly the same as adding; see **mtg-add-cards**.
- Basic lands and tokens are already gone from the collection entirely.
- Before anything large, take a backup: `python3 $MTG_API_REPO/scripts/backup.py`.
  D1 Time Travel also covers the last 30 days.
- Web UI alternative: `$MTG_WEB_URL` → Remove, which forces a
  preview before applying.
