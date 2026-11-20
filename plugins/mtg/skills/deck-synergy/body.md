# Deck synergy

Read only. Never edit the deck, write to the API or buy cards.

Load the **deck-architecture** skill first. Its rule that probabilities are king is the point of this skill: a deck is judged by how its whole 99 fits together, never by its best cards. Every agent brief below includes the path `${XDG_CACHE_HOME:-$HOME/.cache}/claude-skills/deck-architecture/body.md` and tells the agent to read it first.

## 1. Load the deck

From the database, after `set -a; . ~/.mtg-api.env; set +a` (see the **api** skill to find a deck's key):

```sh
python3 <skill base directory>/deck.py DECK_KEY > $SCRATCH/deck.tsv
```

From a pasted list, save it to `$SCRATCH/list.txt` as is, then:

```sh
python3 <skill base directory>/deck.py --list $SCRATCH/list.txt --commander "COMMANDER NAME" > $SCRATCH/deck.tsv
```

Lines like `1 Sol Ring`, `1x Sol Ring (CMM) 400` and `*CMDR*` marks all parse. Ask the user for the commander if the list doesn't make it clear. Any `NOT FOUND` on stderr means a misspelt name, so fix it and rerun. Read deck.tsv before going on.

## 2. Synergy categories

Ask the user for the deck's synergy categories, in chat, and wait for the answer. Say they can give names only, or names with a line each.

If they give none or ask you to come up with them, derive them:
1. Read the commander's oracle text for the events it makes and uses. That's the core of the concept.
2. Follow the chain. Every engine is a flow where something is made, turned into something else, and paid off. Each step is a synergy category, usually an enabler, a converter or multiplier, and a payoff. Aristocrats is fodder, sac outlets, payoffs. Spellslinger is cheap spells, copy and recursion, cast payoffs.
3. 2 to 5 categories. Don't split a step unless the halves do different jobs.

Show the derived categories with a line each and let the user correct them before tagging. If the deck has no clear chain, say so plainly. That's a finding, a low-synergy deck, not something to force.

## 3. Tag every card

Spawn one agent with deck.tsv, the deck-architecture path, the categories and these rules. It writes `$SCRATCH/tags.tsv` with columns `name`, `category`, `also`, `makes`, `uses`, `reason`.

- `category` is the card's primary job. Ramp, Draw, Removal, Protection or a synergy category. The commander's category is `Commander`. Lands are left out unless the engine uses them, landfall for example, and then their category is `Land`.
- `also` is every other category the card really fills in this deck, comma-separated, blank if none.
- `makes` and `uses` are tags for what the card gives the engine and what it needs from it. Only tag what this deck's engine cares about. Generic mana and generic card draw are not tags unless something in the deck triggers on them.
- Use the tag list below. Add a deck-specific tag only when nothing fits, and name it in the reason.
- A card makes a tag by producing it as an effect, or by being a body the engine spends. A creature is fodder in aristocrats, so it makes `creature`. In a spellslinger deck it makes nothing.
- In a tribal deck, being the type is the engine, so tag the type itself, like `dinosaur` or `elf`, and say so in the reason.
- The commander gets makes and uses like any card. It's always in hand, so its links count on every draw.
- Every tag made must be used by something in the deck and the other way round. A tag with only one side is either a mistake or an effect the engine doesn't care about, so drop it.
- Use card names exactly as in deck.tsv.

Tags: `creature`, `token`, `sacrifice`, `death`, `etb`, `leave`, `blink`, `cast`, `instant-sorcery`, `copy`, `draw`, `discard`, `damage`, `lifegain`, `lifeloss`, `counters`, `artifact`, `enchantment`, `landfall`, `graveyard`, `attack`, `tap-untap`, `treasure`, `mana`.

Check it:

```sh
python3 <skill base directory>/graph.py $SCRATCH/deck.tsv $SCRATCH/tags.tsv "<synergy 1>" "<synergy 2>" ...
```

It fails on a missing, repeated or unknown card or category. Send failures back to the tagging agent until it passes.

**Review loop.** Each round, spawn 3 agents with deck.tsv, the deck-architecture path, the categories and tags.tsv. Each looks for tags that link cards that don't really work together, missing tags on cards that do, and wrong categories. Rules details count here, like "another creature", exact damage amounts or who controls the source. Each returns "no meaningful change" or a list of fixes, card, change and why. Apply fixes 2 of 3 back, or that are clearly right on the oracle text. Rerun graph.py. Stop when a round applies nothing, or after 3 rounds with the disputes listed.

## 4. Score

graph.py builds the graph, where two cards are linked when one makes a tag the other uses, and the commander is always in hand. It simulates 20,000 draws at turns 3, 5 and 7, counting 7 + T cards seen. The score adds three groups.

- **Coherence, 40.** Measured on engine cards, those in a synergy category as primary or also. Plain ramp, draw and removal have no tags and don't count against it. How often a drawn engine card has a live partner in hand at turn 5, 20 points. Engine share, the part of the engine in the largest linked cluster, 10. Multi-role share across all spells, 10.
- **Structure, 20.** Lands plus ramp, draw, removal, protection and engine cards against the deck-architecture baseline, 4 each. A card counts toward every category it fills. Pass `--base Mana=50` and the like when the user's plan moves the baseline.
- **Speed, 40.** Average spell mana value, 15. Removal and protection at 2 or less, 10. Ramp at 1 or less, 8. Nonland tutors, 7. This group is what separates a coherent casual deck from cEDH.

The weights aim for a cEDH deck in the 90s, a tuned high-power deck in the 70s, a coherent casual deck around 50 to 60, and a pile of good cards with no engine in the 30s. Only the casual end is tested so far, a Pantlaza precon scored 56.

The hubs section shows what happens to the engine without each of the 3 most linked cards. A big drop means the deck leans on one card. In tribal decks every member links to everything, so hubs barely move and that's expected. Orphans are spells with no link at all. Dangling tags point at a half-built step in the chain, or a tagging mistake.

## 5. Output

In chat, give the score and the component table, then the 2 or 3 biggest things holding the score down, in terms of the whole deck, never one card.

Write the full report to `~/Documents/mtg/<deck name>/synergy.md`, with the deck name from deck.py's stderr, or a name the user gives for a pasted list. It holds the categories and how they were chosen, all of graph.py's output, every card with its category, also, makes and uses, and a short log of each review round. Overwrite any earlier synergy.md for the same deck. Give the user the full path.

## Change log

- 2026-11-20: Coherence measured on engine cards only, synergy added to structure, tribal type tags, no one-sided tags. From a test run on a Pantlaza precon that scored 50.
- 2026-11-20: Created. Makes and uses tags build the graph, draws are simulated, score is coherence 40, structure 20, speed 40.
