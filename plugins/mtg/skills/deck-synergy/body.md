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
4. In a combo deck the tutors are part of the engine, so Tutors can be a category of its own.

Show the derived categories with a line each and let the user correct them before tagging. If the deck has no clear chain, say so plainly. That's a finding, a low-synergy deck. Still name its loose themes as categories so graph.py can run, and the score will show how loose they are.

## 3. Tag every card

Spawn one agent with deck.tsv, the deck-architecture path, the categories and these rules. It writes `$SCRATCH/tags.tsv` with columns `name`, `category`, `also`, `makes`, `uses`, `reason`, `finds`.

- `category` is the card's primary job. Ramp, Draw, Removal, Protection or a synergy category. The commander's category is `Commander`. Lands are left out unless the engine uses them or they fill another role, a landfall land or a channel land that removes something, and then their category is `Land`. A card that fits no category goes in its nearest one with no `also`.
- `also` is every other category the card really fills in this deck, comma-separated, blank if none. Add `Elite` to a single-role card that does its one job exceptionally well, among the best cards ever printed for that job at its cost, like Force of Will or Sol Ring. Elite counts toward the multi-role share, per the deck-architecture rule. Be strict, a good card isn't Elite.
- `finds` is only for tutors, what they can fetch, semicolon-separated. `any`, a card type like `creature` or `artifact` (front face only), a tag the target makes, an exact card name, or `mv=3` for transmute. Respect the limits, Enlightened Tutor finds `artifact; enchantment`, Trophy Mage finds a card name for each 3-mana artifact. Land tutors are ramp, not tutors. The simulation has each tutor fetch the card that links best to what's already there.
- `makes` and `uses` are tags for what the card gives the engine and what it needs from it. Only tag what this deck's engine cares about. Generic mana and generic card draw are not tags unless something in the deck triggers on them.
- Use the tag list below. Add a deck-specific tag only when nothing fits, and name it in the reason.
- A card makes a tag by producing it as an effect, or by being a body the engine spends. A creature is fodder in aristocrats, so it makes `creature`. In a spellslinger deck it makes nothing.
- In a tribal deck, being the type is the engine, so tag the type itself, like `dinosaur` or `elf`, and say so in the reason.
- The commander gets makes and uses like any card. The simulation puts it in play once there's mana for it, so a cheap commander's links count almost every draw and a 10-drop's rarely do. Tag a flip commander by both faces.
- Give every makes and uses tag a strength, like `dinosaur:3`. 3 is strong, the pair is the engine firing at full value, like Pantlaza with a high-toughness Dinosaur or a sac outlet with a death payoff. 2 is solid, a real link that does real work. 1 is weak, incidental, like an anthem or a minor bonus. A link counts the weaker of its two sides, so a 1-toughness Dinosaur is `dinosaur:1` even though Pantlaza uses `dinosaur:3`. Be stingy with 3. Save it for the deck's main engine firing at full value, never for a link that's merely good, since that's what separates a tight engine from a loose one. When a strength depends on stats, like toughness for Pantlaza, set the cut-offs once from the pt column, write them in the first reason, and apply them to every card. graph.py fails on a tag without a strength.
- Don't tag the same link twice. If every Dinosaur entering is the whole point, `dinosaur` covers it, so don't add `etb` at the same strength. Two cards feeding each other both ways is a loop, not a duplicate, so tag both directions.
- Every tag made must be used by something in the deck and the other way round. A tag with only one side is either a mistake or an effect the engine doesn't care about, so drop it.
- Use card names exactly as in deck.tsv.

Tags: `creature`, `token`, `sacrifice`, `death`, `etb`, `leave`, `blink`, `cast`, `instant-sorcery`, `copy`, `draw`, `discard`, `damage`, `lifegain`, `lifeloss`, `counters`, `artifact`, `enchantment`, `landfall`, `graveyard`, `attack`, `tap-untap`, `treasure`, `mana`, `crew`, `infinite-mana`, `library`.

Check it:

```sh
python3 <skill base directory>/graph.py $SCRATCH/deck.tsv $SCRATCH/tags.tsv "<synergy 1>" "<synergy 2>" ...
```

It fails on a missing, repeated or unknown card or category, or a tag without a strength. Send failures back to the tagging agent until it passes.

**Review loop.** Each round, spawn 3 agents with deck.tsv, the deck-architecture path, the categories and tags.tsv. Each looks for tags that link cards that don't really work together, missing tags on cards that do, strengths set too high or too low, Elite on cards that aren't, tutors with wrong or missing finds, and wrong categories. Rules details count here, like "another creature", exact damage amounts or who controls the source. Each returns "no meaningful change" or a list of fixes, card, change and why. Apply fixes 2 of 3 back, or that are clearly right on the oracle text. Rerun graph.py. Stop when a round applies nothing, or after 3 rounds with the disputes listed.

## 4. Score

graph.py builds the graph, where two cards are linked when one makes a tag the other uses, weighted by the tag strengths. Each shared tag counts the weaker of its make and use sides, and a pair takes its strongest shared tag. Then it plays 10,000 games to turn 7, seeing 7 + T cards by turn T. Each turn it plays a land, preferring an untapped one, and casts ramp cheapest first. Rocks make mana right away, dorks and land fetchers from next turn, and rituals and sacrificed sources once. Output comes from the card's Add text, so Sol Ring is 2 and Mana Vault 3. It casts the commander once there's mana for it, and each tutor seen fetches the card that links best to what's already there. The score adds three groups.

- **Coherence, 40.** Measured on engine cards, those in a synergy category as primary or also. Plain ramp, draw and removal have no tags and don't count against it. Live synergy at turn 5, 20 points, the average strength of each drawn engine card's best link to something else in hand, out of 3. Weighting is what stops tribal decks from maxing this out, since every Dinosaur links to every Dinosaur payoff but most of those links are weak. Engine share, the part of the engine in the largest cluster following only links of 2 or more, 10. Multi-role share across all spells, Elite included, 10.
- **Structure, 10.** Mana, meaning lands plus ramp, then draw, removal and protection against the deck-architecture baseline, 2.5 each. A card counts toward every category it fills. Pass `--base Mana=50` and the like when the user's plan moves the baseline. Every functional deck gets most of these, so they're worth little.
- **Speed, 50.** Mana on turn 3 from the simulation, 20. Average spell mana value, 10. Removal and protection at 2 or less, 10. Tutors, 10. Pitch spells like Force of Will count as costing 1. This group is what separates a coherent casual deck from cEDH.

Calibration, from real lists tagged under these rules:

| Deck | Bracket | Score |
|---|---|---|
| Najeela cEDH | 5 | 86 |
| Kinnan cEDH Primer 2026 | 5 | 85 |
| Veloci-Ramp-Tor precon | 2 | 43 |
| Oops, All Jace! | 1 | 37 |
| Bracket 1 Progenitus | 1 | 28 |

So roughly, 85 and up is cEDH, 40s is a precon, and under 35 is a bracket 1 pile. 100 is a cEDH deck with nothing left to improve. The simulation doesn't model commander mana abilities like Kinnan's, so mana-doubling commanders read a little low.

The hubs section shows what happens to the engine without each of the 3 cards with the most links of 2 or more. A big drop means the deck leans on one card. In tribal decks every member links to everything, so hubs barely move and that's expected. Orphans are engine cards with no link at all. Plain ramp, draw and removal aren't listed, since they don't need links. Dangling tags point at a half-built step in the chain, or a tagging mistake.

## 5. Output

In chat, give the score and the component table, then the 2 or 3 biggest things holding the score down, in terms of the whole deck, never one card.

Write the full report to `~/Documents/mtg/<deck name>/synergy.md`, with the deck name from deck.py's stderr, or a name the user gives for a pasted list. It holds the categories and how they were chosen, all of graph.py's output, every card with its category, also, makes and uses, and a short log of each review round. Overwrite any earlier synergy.md for the same deck. Give the user the full path.

## Change log

- 2026-11-20: Tested on 2 cEDH lists, a precon and 2 bracket 1 decks. Tutors get a finds column, link to what they fetch and fetch in the simulation. Elite single-role cards. One simulation handles mana by source type, tapped lands, pitch spells and casting the commander. Weights moved to coherence 40, structure 10, speed 50.
- 2026-11-20: deck.tsv has power and toughness, strengths are required, no duplicate tags for one link.
- 2026-11-20: Tag strengths 1 to 3 weight the links, so tribal decks stop maxing coherence. Speed simulates mana on turn 4 instead of counting fast mana.
- 2026-11-20: Coherence measured on engine cards only, synergy added to structure, tribal type tags, no one-sided tags. From a test run on a Pantlaza precon that scored 50.
- 2026-11-20: Created. Makes and uses tags build the graph, draws are simulated, score is coherence 40, structure 20, speed 40.
