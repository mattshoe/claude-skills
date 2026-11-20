# Analysing a deck

Analysis and card suggestions only. Never edit the deck, write to the API or buy cards.

Load the **deck-architecture** skill before judging anything. It holds the categories, the baseline counts and the multi-role rule every judgment here rests on. Every subagent brief that judges cards, the combo hunt, the math check and the fresh-eyes review, includes the path `${XDG_CACHE_HOME:-$HOME/.cache}/claude-skills/deck-architecture/body.md` and tells the agent to read it first, since subagents don't load skills on their own.

Read the **api** skill for the collection API. Load config with `set -a; . ~/.mtg-api.env; set +a`.

## Start every time

```sh
python3 <skill base directory>/deck.py DECK_KEY > $SCRATCH/deck.tsv
```

It writes qty, name, role, cost, mv, type, game_changer and oracle text for every card, from one deck query and batched Scryfall calls. Read it before saying anything about the deck. Brief subagents with this file, not with your own summary of the deck.

Then read the commander's oracle text word by word and write down exactly what triggers it. The engine is where the deck's real rules are. Things that went wrong on one deck:
- "Another source you control" leaves out sources an opponent controls, like an emblem they own.
- "Exactly 1 damage" means a source dealing 2 doesn't count, and copies of the commander that deal 2 don't trigger each other.
- A mandatory trigger can hit the user too. Painlands and Talismans then cost extra life. Say so once, and if they keep the card, drop it.

## Known combos and mana

Two scripts run on deck.tsv, each one call or no calls at all:

```sh
python3 <skill base directory>/spellbook.py $SCRATCH/deck.tsv > $SCRATCH/combos.tsv
python3 <skill base directory>/mana.py $SCRATCH/deck.tsv
```

spellbook.py lists every combo Commander Spellbook knows in the deck, from one call for the whole list. mana.py plays 10,000 games of lands and ramp and prints the average mana on turns 1 to 6, and how often the deck is ahead of curve. It reads ramp from oracle text and lists every source it found, so check that list before trusting the numbers. Use the mana table when judging ramp, curve or whether the deck can cast its payoffs on time.

## Category breakdown

Run the **deck-categories** skill on the deck. It finds the synergy categories and allocates every card to Ramp, Draw, Removal, Protection, Multipliers, a synergy category or Lands. Show its count table with a Synergy total, which is the sum of the synergy categories, against the deck-architecture baseline, plus its multi-role count. Use its categories and allocation in the rest of the analysis, for example to name which category a suggested card fills or which one a combo depends on. Skip it when the user asks a narrow question, like a single combo's odds.

Then find the orphans, cards in a synergy category that work with nothing else in the deck. Spawn one agent with deck.tsv, the deck-architecture path and the allocation. For each synergy-category card it names the other cards in the deck it actually works with, by oracle text and the deck's real plan, and lists the ones with none. Orphans are the first cut candidates, subject to the hard rules.

## Hard rules

These come from the user and are not up for debate. They apply to any card an analysis calls weak. Pass them to every subagent as hard rules.
- Never suggest cutting board wipes, lands, free mana rocks, card draw or protection unless the user asks. They pick their protection count on purpose.
- Redundancy is deliberate. The user thinks in odds of drawing one of several, so "it overlaps with X" or "it's your 7th counterspell" is never a reason to cut.
- Check the deck list before you suggest a card. Suggesting a card that's already in the deck is the worst miss.
- Never claim no more cards exist for a role. Search first.
- Respect the bracket. If the user says no more game changers, the Scryfall query gets `-is:gamechanger` and the `game_changer` column shows the current count.
- Respect how the deck wins. If its creatures don't attack, don't suggest combat triggers. If it's an ETB deck, don't suggest instant or sorcery payoffs.
- Don't relitigate. When the user says a card stays, it stays.

## Suggesting cards

Search Scryfall, never pick from memory:

```sh
curl -s -G https://api.scryfall.com/cards/search -A mtg-deck-analyzer/1.0 \
  --data-urlencode 'q=id<=ur f:commander -is:gamechanger o:"draw a card" (o:"deals damage" or o:whenever)' \
  --data-urlencode 'order=edhrec'
```

Use the commander's colours for `id<=`, and build oracle filters from the engine you wrote down. Drop every hit that's already in deck.tsv. The best picks are often synergy cards no generic list shows, like a card that draws on the exact event the commander creates.

Check ownership of the shortlist with one query:
`SELECT name, owned, in_decks, free FROM card_usage WHERE owner_id = $MTG_OWNER_ID AND name_norm IN (...)`.
Bulk means `free > 0`, never cards claimed by a deck.

Give each pick a one-line reason tied to this deck's engine, and name every category it fills. Prefer picks that fill 2 or more. When the user asks what to cut, pick from cards that break none of the hard rules, start with single-role cards that are only average at their one job, and say what the cut card did.

## Finding combos and loops

Spawn 5 subagents in parallel. Write one brief file and point each agent at it. The brief holds:
- the path to deck.tsv
- the deck-architecture body path, to read first
- the commander engine you wrote down
- the loops already known, marked "do not report", including every combo in combos.tsv
- the rules traps below

Give each agent a different starting angle:
1. Token makers, sac outlets, ETB and death triggers.
2. Copy effects, clones, untap and blink.
3. Draw triggers, damage triggers, and anything that turns one into the other.
4. Mana engines, cost reducers, and anything that makes mana from creatures.
5. A card by card sweep that tries to break every loop before reporting it.

For each loop, ask for the cards, the step by step sequence, the net gain per iteration, whether it wins alone or needs a finisher, and a confidence level. Also ask for near misses that are one card short.

Rules traps to put in the brief:
- Mandatory versus optional triggers.
- Who controls the source.
- Summoning sickness on tap abilities, and a transformed permanent counts as a new object.
- The legend rule. Token copies of a legend are legendary, except copies from Spark Double.
- Exact damage amounts.
- Equipment that kills the creature it's attached to, like Skullclamp on a 1/1.
- Mana that is actually net positive.

**Check every claimed loop yourself before you tell the user.** Agents miss per-iteration costs. Five agents once called Reflection of Kiki-Jiki plus Pestermite infinite, but Reflection costs {1} to activate, so it needs Ashnod's Altar like any other Reflection copy. When a near miss only fills a slot of a known loop, it adds a piece to that loop, not a new loop.

Count loops by their distinct card sets, not by the number of piece combinations.

## Combo odds

Write the loops as `combos.json` (see `combos.example.json`): each combo is a list of slots, each slot a list of the cards that fill it. Then run

```sh
python3 <skill base directory>/odds.py $SCRATCH/combos.json
```

It gives exact odds by turn, with and without extra draw, plus each combo's own odds and a Monte Carlo check. The assumptions:
- The commander is not in the library.
- Library is 99 cards.
- Cards seen by turn T is 7 + T, since multiplayer has no skipped first draw.
- Extra draw adds Binomial(turns since `from_turn`, `p`) cards.
- Mana, removal, mulligans, tutors and slow pieces like sagas are ignored.

Tell the user the results are a floor if the deck has tutors.

Lead with the table. Name the bottleneck, meaning the single card in the most combos. Adding a combo that needs the bottleneck barely moves the total, so say that when it's true.

When the user wants the math checked, spawn 3 to 5 subagents. Give them the combo list and the model but not your numbers, and ask each for a different method. Report whether they agree.

## Fresh-eyes review

When the user asks for a review, score or win rate, spawn 3 agents with the deck.tsv path, the deck-architecture body path and the hard rules, and nothing else. Give them no conclusions of yours, so they aren't anchored. Ask each for:
- Synergy gaps, and category counts against the deck-architecture baseline.
- The weakest 5 cards, which must not include protected categories.
- A 0 to 100 score.
- A win rate at the deck's bracket in a 4 player pod.
- What beats the deck.

Report where they agree and where they split. Drop any suggestion that breaks a hard rule, and don't pass it on.

## Change log

- 2026-11-20: Loads deck-architecture first and passes it to every judging subagent. Suggestions and cuts weigh how many categories a card fills.

- 2026-11-20: Added spellbook.py for known combos, mana.py for mana by turn, and the orphan check. They came from the deleted deck-synergy skill, whose score measured how fast linked cards showed up, not deck strength.
- 2026-11-01: Added the deck-categories step.
- 2026-11-01: Created from analysing one Izzet ping deck: engine read, loop hunt, combo odds, blind review, with deck.py and odds.py. odds.py matched 5 independent agents to 0.05 points. Cut to analysis and card suggestions, no swaps or buying.
