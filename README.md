# claude-skills

Claude Code skills for a Magic: The Gathering collection, packaged as a plugin marketplace.

```
/plugin marketplace add mattshoe/claude-skills
/plugin install mtg-api@mattshoe-skills
```

| Plugin | What |
|---|---|
| mtg-api | read and query a collection through an MTG API deployment |
| mtg-add-cards | add cards to the collection |
| mtg-remove-cards | remove cards from the collection |
| mtg-build-deck | build a Commander deck from unassigned cards |
| mtg-system | maintain the API deployment itself |
| card-buyer | fill local game store and TCGPlayer carts from a card list |

## Config

The skills hold no URLs, owners, stores or credentials. Put yours in `~/.mtg-api.env`, `chmod 600`:

```
MTG_API_URL=https://your-worker.example.workers.dev
MTG_WEB_URL=https://your-site.example.com
MTG_OWNER=yourname
MTG_OWNER_ID=1
MTG_ADMIN_PASSWORD=...
MTG_API_REPO=/path/to/mtg-api
MTG_BACKUP_DIR=/path/to/backups
CARD_STORES=store-one.example.com,store-two.example.com
CARD_STOREPASS=store-two.example.com=STOREID
```

Writes to a collection need `MTG_ADMIN_PASSWORD`, which only the deployment's owner has. Installing these skills gives no access to anyone else's collection.
