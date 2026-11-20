# Deck builder

Load the **deck-architecture** skill first. Its categories, baseline counts, multi-role rule and "probabilities are king" are the frame for every choice here. Read the **api** skill for the collection API, and load config with `set -a; . ~/.mtg-api.env; set +a`.

The deck is never added to the collection database by this skill. That only happens when the user approves it afterwards, through `POST /decks/create` with a dry run shown first, per the api skill.

## 1. Ask

The user names the commander. Then ask, in one message, and wait:
- **Scope.** Only cards free in their collection, or any card in the game.
- **Budget.** The most they'll spend. Only cards they'd have to buy count against it. A card they already own costs nothing.

## 2. The plan

Read the commander's oracle text word by word and write down:
- **The engine.** What it makes, what it uses, what it rewards.
- **The win.** How this deck actually ends a game. It can be combat, voltron, drain, combo, alternate win or something else. Name it plainly, it's the thing every later choice serves.
- **Synergy categories.** The steps of the engine, usually an enabler, a converter, and a payoff. Aristocrats is fodder, sac outlets, payoffs. Voltron is evasion, protection and pump for the commander. 2 to 5 categories, each with a one-line definition.
- **Counts.** Start from the deck-architecture baseline, 37 lands, 10 ramp, 10 draw, 8 removal, 8 protection, 6 multipliers, 20 synergy. Move a count only with a reason tied to this deck. Landfall wants more lands, a deck with nothing worth doubling wants fewer multipliers, a voltron deck wants more protection, a deck that tutors constantly can run less draw. Write each move and its reason. The total is 99.

Show the plan to the user in a few lines and keep going unless they object.

## 3. Pick the spells

Go category by category: each synergy category first, then multipliers, ramp, draw, removal, protection. Keep one running list.

**Where candidates come from.**
- Collection scope: free copies only, from one query per category, filtered to the commander's colour identity. Bulk means `free > 0`, never cards claimed by a deck.
  `SELECT c.name, u.free, c.type_line, c.oracle_text FROM card_usage u JOIN cards c ON c.owner_id = u.owner_id AND c.name_norm = u.name_norm WHERE u.owner_id = $MTG_OWNER_ID AND u.free > 0 AND ... GROUP BY u.name_norm`
  Use `card_search MATCH` for oracle text, per the api skill's gotchas.
- Any-card scope: Scryfall search, one query per category, never picking from memory. `id<=<colours> f:commander` plus oracle filters built from the engine, `order:edhrec`. Also check what the user owns, since owned cards are free against the budget.
- Commander Spellbook and EDHREC can suggest, but every pick is checked against its oracle text.

**How to choose.**
- Prefer cards that fill 2 or more categories, and most of all ones that fill a synergy category plus a core one. A removal spell that also feeds the engine beats one that only removes.
- A card that fills one category has to do that one thing very well, among the best at it for its cost.
- Win plans need redundancy. Never one card as the plan unless it's the commander, payoffs are a category.
- Double-faced cards never count as lands.
- Watch the curve. Most spells at 3 or less, few above 5 unless the deck ramps hard.
- Respect the bracket the user asks for. If they name none, avoid game changers and two-card infinite combos unless the commander's plan is one.

For each pick write its categories, primary first. When every category is full, list any category that ended short and why.

## 4. The mana base

With the spells chosen, write the list to `$SCRATCH/list.txt`, one `1 Name` per line, the commander marked `*CMDR*`, plus the land count's worth of placeholder basics. Then:

```sh
python3 <skill base directory>/deck.py $SCRATCH/list.txt > $SCRATCH/deck.tsv
python3 <skill base directory>/audit.py $SCRATCH/deck.tsv --budget <dollars> --scope <any|collection>
```

audit.py's mana table is the tool for land distribution, use it and nothing else. It applies Frank Karsten's 99-card method to every spell and gives the coloured sources each colour needs. Then choose the lands:
- Nonbasics first: duals and fetches in the deck's colours, utility lands only when they serve the engine. Owned lands first, they're free. In a one-colour deck nearly everything is basics.
- Fill the rest with basics, split so every colour reaches its needed count.
- Rerun deck.py and audit.py until every colour meets its number. If a colour can't get there, say which spell is asking and consider cutting it for an easier one.

## 5. Audit and budget

audit.py checks legality, 100 cards, one commander, singleton, colour identity and Commander legality, and prices everything that has to be bought, cheapest printing, from one collection query and a few Scryfall searches. Basic lands are never bought.

While it reports problems, fix them and rerun. Over budget: swap the most expensive buys first for cheaper cards that fill the same categories, owned ones before bought ones, and rerun. Keep the multi-role picks if you can, cut a single-role expensive card before a cross-category one. Stop when audit.py exits clean.

## 6. Name it

Give the deck a fun, cheeky name of exactly two words that fits the commander and the plan.

## 7. Drive

Find or create `MTG/Decks/<deck name>` in Google Drive. `MTG` sits in My Drive's root, search `parentId = 'root' and title = 'MTG'` with the folder mime type, then `Decks` inside it, creating either when missing.

Write two files there:
- **`<deck name>.txt`**, plain text, uploaded with `disableConversionToGoogleType` so it stays a text file. Only the decklist: one `1 Card Name` per line, basics as `N Forest`, commander included. No headings, no comments, no blank lines, nothing else.
- **`<deck name> Guide`**, a Google Doc. The commander and the plan in a short paragraph, the synergy categories with their key cards, the counts and why they moved from the baseline, how to play it, early, mid and late game, the key turns and what to protect, how it wins, what beats it, and mulligan advice. Also the cost: what was bought and for how much.

## 8. Fetch list

```sh
python3 <skill base directory>/fetch.py "<deck name>" $SCRATCH/list.txt
```

It saves the 100 cards as a Fetch list in the user's app, the same on web and phone. It shows up unsearched, so the user taps Find to see where each card is.

## 9. Report

In chat: the name, the plan in two lines, the counts table, what has to be bought and the total against the budget, the Drive folder link, and that the Fetch list is saved. Then ask whether to add the deck to the collection. Only on a yes, run `POST /decks/create` as a dry run, show what it would move and buy, and apply it on a second yes.

## Change log

- 2026-11-20: Multipliers are a category, 6 by default.
- 2026-11-20: Created. Karsten's method checked against his published 99-card figures. Fetch lists go through `/fetch-lists` with the admin token, added to the API for this.
