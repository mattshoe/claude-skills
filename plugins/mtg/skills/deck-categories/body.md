# Deck categories

Read only. Never edit the deck. Read the **api** skill for the collection API, and load config with `set -a; . ~/.mtg-api.env; set +a`.

## 1. Load the deck

```sh
python3 <skill base directory>/deck.py DECK_KEY > $SCRATCH/deck.tsv
```

It prints the deck name to stderr. The commander is left out. Lands get their own Lands category, which is only a count: check.py counts single-faced lands, utility lands included. Double-faced cards never count as lands, even when the deck files them as lands, so they get allocated like any spell. Lands are never allocated, reviewed or listed by name. The table totals 99.

## 2. Synergy categories

1. **Proposal.** Spawn 5 agents in parallel. Each gets only the deck.tsv path and this brief, none of your views:
   - Work out the deck's intent, meaning how it plans to win.
   - Break the plan into its distinct synergy categories, 2 to 5 at most. An aristocrats deck has fodder, sac outlets and payoffs. A go-wide deck has token makers and pumpers.
   - Ramp, Draw, Removal and Protection are fixed categories, so don't propose them.
   - Give each category a name, a one-line definition and 3 example cards.
   - Fewer is better. Only split a category when the two halves do different jobs in the plan.
2. **Merge.** Combine the 5 answers into one candidate list. Keep what most agents found, merge near-duplicates, and note any split.
3. **Adversarial loop.** Each round, spawn 3 agents with deck.tsv and the candidate list. Each one tries to break the list: a category to merge, split, rename or drop, a missing one, or a definition so loose it swallows everything. Each returns either "no meaningful change" or specific changes with reasons. Apply a change when 2 of 3 agents back it, or when one agent's case is clearly right on the cards. Repeat until a round has all 3 agents saying no meaningful change. Stop after 5 rounds and report what's still contested.

## 3. Allocation

The categories are Ramp, Draw, Removal, Protection, then the synergy categories.
- Ramp is mana rocks, dorks, cost reducers, land untappers and extra land drops.
- Draw is card draw and card advantage.
- Removal is burn, destroy, exile, bounce and wipes.
- Protection is counterspells, shroud, hexproof, indestructible and anything that saves your pieces.

1. **One agent allocates.** It gets deck.tsv, the final category list with definitions, and these rules:
   - Every nonland, noncommander card goes in exactly one category. Leave lands out.
   - A card that fits several goes where it does the most work in this deck's plan. Write that judgment in the reason.
   - Output `alloc.tsv` with columns `name`, `category` and `reason`, using card names exactly as in deck.tsv.
2. **Check it.**
   `python3 <skill base directory>/check.py $SCRATCH/deck.tsv $SCRATCH/alloc.tsv Ramp Draw Removal Protection "<synergy 1>" ...`
   It fails on any missing, repeated or unknown card or category. Send failures back to the allocating agent until it passes.
3. **Review loop.** Each round, spawn 3 agents with deck.tsv, the categories and alloc.tsv. Each returns either "no meaningful change" or a list of moves, written as card, from, to and why. A meaningful move fixes a card in the wrong role. A coin-flip between two fair homes doesn't count. Apply moves that 2 of 3 agents back, or that are clearly right on the oracle text. Run check.py after each round. Repeat until a round applies no moves, and stop after 5 rounds with the open disputes listed.

## 4. Output

In chat, show only the table from check.py, with no card names unless the user asks.

Write the full document to `~/Documents/mtg/<deck name>/categories.md`. It holds:
- The deck's intent, in a short paragraph.
- Each synergy category with its definition.
- The count table, including Lands.
- Every nonland card under its category, with the reason. Lands appear only as a count.
- Contested cards, with the other home each one could have.
- A short log of each round: what was proposed, applied and rejected.

Overwrite any earlier categories.md for the same deck. Give the user the full path.

## Change log

- 2026-11-01: Created. Lands are a counted category, never allocated. Double-faced cards never count as lands, the user's rule.
