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

Then fetch the deck's combos from Commander Spellbook, one call for the whole list:

```sh
python3 <skill base directory>/spellbook.py $SCRATCH/deck.tsv > $SCRATCH/deck.combos.tsv
```

graph.py reads `deck.combos.tsv` next to `deck.tsv` on its own. Combos are the only strong links, nobody tags them by hand.

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

Spawn one agent with deck.tsv, the deck-architecture path, the categories and these rules. It writes `$SCRATCH/tags.tsv` with columns `name`, `category`, `also`, `makes`, `uses`, `reason`, `finds`, `mana`, `modifies`, `cards`, `fire`.

- `category` is the card's primary job. Ramp, Draw, Removal, Protection or a synergy category. The commander's category is `Commander`. Lands are left out unless the engine uses them or they fill another role, a landfall land or a channel land that removes something, and then their category is `Land`. A card that fits no category goes in its nearest one with no `also`.
- `also` is every other category the card really fills in this deck, comma-separated, blank if none. Add `Elite` to a single-role card that does its one job exceptionally well, among the best cards ever printed for that job at its cost, like Force of Will or Sol Ring. Elite counts toward the multi-role share, per the deck-architecture rule. Be strict, a good card isn't Elite.
- `finds` is only for tutors, what they can fetch, the commander included, like Sisay finding `legendary` with `fire` for her activation, semicolon-separated. `any`, a card type like `creature` or `artifact` (front face only), a tag the target makes, an exact card name, or `mv=3` for transmute. Respect the limits, Enlightened Tutor finds `artifact; enchantment`, Trophy Mage finds a card name for each 3-mana artifact. Land tutors are ramp, not tutors. The simulation has each tutor fetch the card that links best to what's already there.
- `makes` and `uses` are tags for what the card gives the engine and what it needs from it. Only tag what this deck's engine cares about. Generic mana and generic card draw are not tags unless something in the deck triggers on them.
- Use the tag list below. Add a deck-specific tag only when nothing fits, and name it in the reason.
- A card makes a tag by producing it as an effect, or by being a body the engine spends. A creature is fodder in aristocrats, so it makes `creature`. In a spellslinger deck it makes nothing.
- In a tribal deck, being the type is the engine, so tag the type itself, like `dinosaur` or `elf`, and say so in the reason.
- `mana` is for every mana source, rocks, dorks, rituals, treasure makers and land fetchers. Write the amount and when it works. `now` taps the turn it lands, like Sol Ring `2 now`. `next` works from next turn, like a dork `1 next` or Cultivate `1 next`. `once` is spent a single time, like Dark Ritual `3 once`, Lotus Petal `1 once` or Mana Vault `3 once`. Leave it blank for anything that doesn't reliably make mana, like a card that puts a land in hand. Lands make 1 by default and tapped lands work from next turn, so only give a land a row and a `mana` value when it makes more, like Ancient Tomb `2 now`.
- `modifies` is for cards that change other sources' output while in play. `mana+1` adds 1 to every nonland source, like Kinnan. `land+1` adds to lands, like Mirari's Wake. `all*2` doubles everything, like Mana Reflection. The simulator applies these without knowing the card.
- `cards` is for card draw sources, same format as `mana`. Rhystic Study or Phyrexian Arena is `1 next`, Sylvan Library `1 now`, Brainstorm `2 once`, Night's Whisper `2 once`. Count only reliable extra cards, not conditional ones you can't count on.
- `fire` is extra mana a card needs before its links work, on top of casting it. Najeela is `5` for WUBRG, a sac outlet with a {1} cost is `1`. Blank means 0.
- The commander gets makes and uses like any card. The simulation puts it in play once there's mana for it, so a cheap commander's links count almost every draw and a 10-drop's rarely do. Tag a flip commander by both faces.
- Give every makes and uses tag a strength of 1 or 2, like `dinosaur:2`, by answering three yes or no questions about the link. Does it fire every time, not only sometimes? Does its output grow with the board, not stay fixed? Is it on the deck's main chain, not a side bonus? Two or more yeses is 2, otherwise 1. Write the answers in the reason as `yyn` and the like for any card whose strength isn't obvious. A link counts the weaker of its two sides, so a 1-toughness Dinosaur is `dinosaur:1` even though Pantlaza uses `dinosaur:2`. There's no 3. Combos that win on their own come from Spellbook, and graph.py rejects a 3. When the answers depend on stats, like toughness for Pantlaza, set the cut-offs once from the pt column, write them in the first reason, and apply them to every card. graph.py fails on a tag without a strength.
- Don't tag the same link twice. If every Dinosaur entering is the whole point, `dinosaur` covers it, so don't add `etb` at the same strength. Two cards feeding each other both ways is a loop, not a duplicate, so tag both directions.
- Every tag made must be used by something in the deck and the other way round. A tag with only one side is either a mistake or an effect the engine doesn't care about, so drop it.
- Use card names exactly as in deck.tsv.

Tags: `creature`, `token`, `sacrifice`, `death`, `etb`, `leave`, `blink`, `cast`, `instant-sorcery`, `copy`, `draw`, `discard`, `damage`, `lifegain`, `lifeloss`, `counters`, `artifact`, `enchantment`, `landfall`, `graveyard`, `attack`, `tap-untap`, `treasure`, `mana`, `crew`, `infinite-mana`, `library`.

Check it:

```sh
python3 <skill base directory>/graph.py $SCRATCH/deck.tsv $SCRATCH/tags.tsv "<synergy 1>" "<synergy 2>" ...
```

It fails on a missing, repeated or unknown card or category, or a tag without a strength. Send failures back to the tagging agent until it passes.

**Review loop.** Each round, spawn 3 agents with deck.tsv, the deck-architecture path, the categories and tags.tsv. Each looks for tags that link cards that don't really work together, missing tags on cards that do, strengths whose yes or no answers are wrong, Elite on cards that aren't, tutors with wrong or missing finds, and wrong categories. Rules details count here, like "another creature", exact damage amounts or who controls the source. Each returns "no meaningful change" or a list of fixes, card, change and why. Apply fixes 2 of 3 back, or that are clearly right on the oracle text. Rerun graph.py. Stop when a round applies nothing, or after 3 rounds with the disputes listed.

## 4. Score

graph.py builds the graph, where two cards are linked when one makes a tag the other uses, weighted by the tag strengths. Each shared tag counts the weaker of its make and use sides, and a pair takes its strongest shared tag.

Then it plays 10,000 games to turn 10. It knows nothing about specific cards, only the tags. Each turn it plays a land, preferring an untapped one, casts mana sources cheapest first, applies modifiers, and casts the commander once it can. Each tutor fetches the card that completes the most strong links.

**The engine is online** the first turn the simulation can assemble a castable group of up to 3 cards, in hand, in play, fetched or the commander, that's a Spellbook combo, three cards all linked to each other at 2, or a chain of three at 2 where the middle card links each way through a different role, like fodder into a sac outlet into a death payoff. Each card has to fit one turn's mana, and together they have to fit the mana left over so far, `fire` included. A hub that uses one tag with every spoke doesn't count, so the commander plus two rocks or three tribe members isn't an engine. Spellbook combos of any size count once all their pieces are there. More such groups in the deck means online in more games, which is redundancy, the deck-architecture rule that probabilities are king. Draw sources from the `cards` column make the simulation see more cards, so card advantage speeds the engine up like ramp does.

**The score** comes from the reference decks in `<skill base directory>/reference.tsv`, real lists with known brackets tagged under these rules. Each bracket has a target, 1 at 20, 2 at 40, 3 at 60, 4 at 75 and 5 at 92, and graph.py fits a straight line from online turn to that target across every reference deck. The deck's score is read off the line. To add a reference deck, run graph.py with `--reference "DECK NAME" BRACKET`, then commit reference.tsv.

With 20 reference decks the fit correlation is 0.74. Online turn cleanly separates bracket 1, around turn 9 and later, from everything else, and the fastest cEDH decks come online by turn 4. Brackets 2 to 4 overlap a lot, between turns 5 and 7, so the score is reliable at the ends and rough in the middle. Brackets in the middle differ mostly by card quality and interaction, which the engine turn doesn't measure, and Archidekt brackets are self-reported.

The diagnostics under the score aren't scored. They explain it. No Spellbook combos and few solid links means a loose engine. Low mana on turn 3 means slow ramp. Orphans are engine cards with no link. Dangling tags point at a half-built step in the chain or a tagging mistake. Hubs show the cards in the most combos and with the most solid links, and what the engine looks like without each.

## 5. Output

In chat, give the score, the online-by-turn table, then the 2 or 3 biggest things holding the score down, in terms of the whole deck, never one card.

Write the full report to `~/Documents/mtg/<deck name>/synergy.md`, with the deck name from deck.py's stderr, or a name the user gives for a pasted list. It holds the categories and how they were chosen, all of graph.py's output, every card with its category, also, makes and uses, and a short log of each review round. Overwrite any earlier synergy.md for the same deck. Give the user the full path.

## Change log

- 2026-11-20: Strong links come from Commander Spellbook combos, not tags. Taggers pick 1 or 2 with three yes or no questions, to cut tagger variance.
- 2026-11-20: 20 reference decks across all 5 brackets from Archidekt. Score is a fitted line, correlation 0.74. Chains of three count when the middle card changes role, tutors chain and commanders with finds tutor.
- 2026-11-20: Online needs a strong pair or a fully linked triple, so hubs with loose spokes don't count.
- 2026-11-20: Engine power replaces pairs, so triples and redundancy count. Strength has a test, 3 means the pair alone pushes toward winning. New `cards` and `fire` columns for card draw and activation costs. One-shot mana is spent once.

- 2026-11-20: Score is now the turn the engine comes online, placed among reference decks by bracket. Mana sources and modifiers are tag columns, so the simulator has no card-specific rules.

- 2026-11-20: Tested on 2 cEDH lists, a precon and 2 bracket 1 decks. Tutors get a finds column, link to what they fetch and fetch in the simulation. Elite single-role cards. One simulation handles mana by source type, tapped lands, pitch spells and casting the commander. Weights moved to coherence 40, structure 10, speed 50.
- 2026-11-20: deck.tsv has power and toughness, strengths are required, no duplicate tags for one link.
- 2026-11-20: Tag strengths 1 to 3 weight the links, so tribal decks stop maxing coherence. Speed simulates mana on turn 4 instead of counting fast mana.
- 2026-11-20: Coherence measured on engine cards only, synergy added to structure, tribal type tags, no one-sided tags. From a test run on a Pantlaza precon that scored 50.
- 2026-11-20: Created. Makes and uses tags build the graph, draws are simulated, score is coherence 40, structure 20, speed 40.
