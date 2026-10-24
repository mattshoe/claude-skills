---
name: mtg-build-deck
description: Build a Magic&#58; The Gathering Commander deck for the user out of the cards they own but has not committed to a deck. Use whenever they want a new deck, a deck around a particular commander or theme, or asks what they could build from their bulk - "build me a deck", "what can I make with my spare cards", "make something around +1/+1 counters". Runs an iterative build-grade-revise loop with independent grader panels at every step and writes the finished decklist to notes/. Companion to mtg-add-cards and mtg-remove-cards.
---

# Building a deck from the unassigned collection

The goal is **the most synergistic and powerful deck the pool can produce** — not
a legal one, not an adequate one. The pool is the constraint; power is the
objective. A run that assembles 100 playable cards has failed.

Cards come from the **`bulk_cards`** view — what the user owns and has **not**
committed to an existing deck. Basic lands are untracked and effectively
unlimited; everything else must have a free copy. Never propose a card they do
not own.

The collection is the REST API at `$MTG_API_URL`.
Read the **mtg-api** skill for the data shape and the query gotchas.

## Where the pool comes from

```bash
q() { curl -s -X POST $MTG_API_URL/query \
  -H 'content-type: application/json' -H 'user-agent: mtg-cli/1.0' \
  -d "{\"sql\":$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$1"),\"fmt\":\"objects\"}"; }

# what is actually spare
q "SELECT name, free FROM bulk_cards WHERE owner='$MTG_OWNER' ORDER BY free DESC LIMIT 50"

# legends they could build around, by how much of the pool shares their identity
q "SELECT c.name, c.color_identity FROM cards c JOIN card_usage u
     ON u.name_norm = c.name_norm AND u.owner = c.owner
    WHERE c.owner='$MTG_OWNER' AND u.free > 0 AND c.type_line LIKE '%Legendary Creature%'
    GROUP BY c.name_norm"
```

> **The old `deckpool.py` and `deckcheck.py` read the frozen Drive shards.**
> Their *pool* is a snapshot from before the migration and will offer cards they
> no longer has and miss everything they have acquired since. Do not use them to
> decide availability. Their rubric and scoring logic is still worth reading;
> the data under it is not.

`deckcheck.py` proves legality mechanically — exactly 100, singleton, colour
identity, commander legality, every card free in bulk. **Never** ask a grader to
check any of that; it is settled before a grader sees anything.

## The loop

Seven gates. At each one: build the artifact, send it to **3 independent graders**,
revise, re-grade. Advance only when all three concede.

| Gate | Artifact | Graded on |
|---|---|---|
| 1 | Commander + gameplan | Is this the best seam in the pool, and the best commander for it |
| 2 | ~150-200 card shortlist | Every role covered; no strictly-better unused card missed |
| 3 | The ~62 nonland spells | Interaction, draw, tutors, synergy density |
| 4 | Mana base | Fixing, curve, land count |
| 5 | Assembled 100 | Full 0-100 score, after `deckcheck.py` passes |
| 6 | Adversarial review | Ceiling, and what beats this deck |
| 7 | **Playtest review** | **Pure judgment: would you sleeve this and play it?** |

### Gate 1 — pick the seam before the commander

Do **not** start from a commander unless the user named one. Starting from a legend
caps the deck at whatever that legend happens to support. Run `--seams` and
`--commanders` first, find where the pool is genuinely deep, then choose the
commander that exploits it. The artifact must justify the winner **over the
named runners-up**.

If the user named a commander, skip the search but still run `--seams` so the build
knows what the pool can actually feed.

### The pass rule is a swap test, not a score bar

A score threshold rewards adequacy. A gate passes only when **no grader can name
a specific card still in the pool that would improve the artifact, and say why.**
Graders must attempt the swap and fail before conceding.

- Graders receive **only** the artifact, the rubric, and database access. Never
  the builder's reasoning, never prior grades, never each other's scores.
- Every grader **must** name its single strongest objection even when passing. A
  grader that raises nothing is treated as a failed grade and re-run once.
- **ONE grader saying REVISE fails the gate.** Not a majority vote. If any grader
  returns REVISE, the gate has not passed — revise the artifact and **re-run the
  full panel on the revised artifact**. Do not carry a REVISE forward as a "known
  issue" and proceed. Do not treat 2 PASS / 1 REVISE as a pass.
- **A PASS carrying an objection is still a signal.** If two graders pass but both
  name the same objection, that objection is real and the artifact is wrong.
  Revise and re-grade it.
- **Re-grading means a new panel on the new artifact.** Spawn fresh graders. Tell
  them nothing about the previous round — no prior scores, no prior objections,
  no "we already fixed X". They must reach their verdict independently or the
  second round is theatre.
- **Maximum 3 revision rounds per gate.** On the third failure, stop and put the
  disagreement to the user rather than grinding.
- A run where every gate passes first try means the graders were not adversarial
  enough — say so rather than reporting a clean sweep.

### Gate 7 — the playtest panel, and it is the one that matters

The final gate. Graders get **the decklist and nothing else**: no rubric, no
score, no `deckcheck.py`, no prior grades, no build reasoning. They are asked to
judge it the way a player would.

They answer, in their own words:

- Walk through three games. What does turn 1-3 look like, turn 4-6, turn 7+?
- How many turns before the deck is doing the thing its commander is for?
- What does a bad draw look like, and how often?
- Is there a card here you would cut on sight, and why?
- Does the deck do what its own description claims?
- **Would you sleeve this up and play it?**

A grader that answers only in generalities is re-run. The verdict is PLAY or
REBUILD — not a number. **One REBUILD fails the gate.**

This gate exists because a build passed all six preceding gates, scored 68/100,
and was unplayable in its first real game: 55% mana sources, four creatures drawn
in fifteen turns. Every earlier gate was reading a rubric, so every earlier gate
missed it. A rubric measures what someone thought to measure; this gate is the
check on that.

**No rubric arithmetic is allowed in a Gate 7 verdict.** If a grader cites a
score, discard the grade and re-run it.

### Any gate may be thrown out, at any point, by the root agent

The root agent running the build has standing authority to **discard the work and
restart from any earlier gate — including Gate 1 — at any moment**, without asking
and without needing a gate to formally fail.

Use it when the evidence says the foundation is wrong, not merely improvable:

- a later gate reveals the commander cannot do what the seam requires
- the pool turns out not to support the plan once real cards are read
- the deck is being kept alive by patching rather than by working
- a playtest contradicts the build's premise
- **the accumulated effort is the main reason the build is still alive**

That last one is the real hazard. Nine grader panels and six passed gates create
enormous pressure to keep patching rather than admit the seam was wrong. Sunk cost
is not evidence. A build that has consumed a lot of work and is still limping is
*more* likely to need restarting, not less.

Restarting is cheap relative to shipping a deck that does not work. Say plainly
that it is being restarted and why, then start over.

### Grader prompt template

Spawn each grader as a separate subagent so they cannot see one another:

> You are grading one step of a Commander deck build, independently. Do not
> assume the builder was right about anything.
>
> Pool: only cards in the `bulk_cards` view for owner $MTG_OWNER are available.
> Verify availability yourself against the API, not from the artifact.
> Rubric: read `deck-scoring-system/` in the mtg folder.
>
> ARTIFACT: <the artifact only — no rationale>
>
> Your job:
> 1. Score it against the relevant rubric criteria, showing the arithmetic.
> 2. **Attempt a swap.** Query the remaining pool and try to name a specific card
>    that would make this better. Give the card, what it replaces, and why.
> 3. State your single strongest objection, even if you are passing it.
>
> Answer: PASS or REVISE, the swap you found (or "none found, and here is what I
> searched"), and your objection.

### Gate 7 grader prompt — deliberately different

Gate 7 graders must **not** be given the rubric, the score, or `deckcheck.py`.
Handing them a rubric is what caused the failure this gate exists to catch.

> You are reviewing a finished Commander decklist as a player, not as a scorer.
> There is no rubric and no score. Do not compute one, and do not open
> `deck-scoring-system/` or `deckcheck.py`. If you find yourself producing a
> number, stop.
>
> DECKLIST: <the 100 cards, and the one-line description of what the deck is
> supposed to do — nothing else>
>
> You may read any card's text from the API. Then answer as a player:
>
> 1. Walk through three games in your head. What happens on turns 1-3, 4-6, 7+?
> 2. How many turns before the deck is actually doing the thing its commander is
>    for? Be specific about what has to be on the battlefield.
> 3. What does a bad draw look like here, and how often does it happen?
> 4. Name any card you would cut on sight, and say why.
> 5. Does the deck do what its description claims? Where does the claim break?
> 6. **Would you sleeve this up and play it in a pod? Why or why not?**
>
> Answer PLAY or REBUILD, then your reasoning in plain language. If REBUILD, say
> how far back it needs to go — a few card swaps, the whole spell list, or the
> commander itself.

## Output

One markdown file in `notes/`, named `YYYY-MM-DD-<deck-name-slug>.md`, in the same shape
as the decks already in the database: metadata block, `## Commander (1)`,
`## Nonland spells ...`, `## Lands (n)`. Include the final 0-100 score, the
bracket, and a short "what caps this deck" section naming the pool gaps.

### Name the deck

Every build gets a real name, not a description. **Two words maximum.** Simple,
catchy, the kind of thing printed on the box — names like Blight Curse,
Sneak Attack, World Shaper, Counter Blitz. Match that register exactly.

The name comes from what the deck *does at the table*, not from its commander and
not from its mechanics. A toughness-matters wall deck is **Immovable** or **Wall
Street**, never "Felothar Toughness Combo" or "BGW Defenders". Say it out loud —
if it sounds like a spreadsheet label, it is wrong.

Rules:
- Two words, or one if one is stronger
- No commander name, no colour or guild names, no "deck"/"build"/"brew"
- No generic mechanic labels ("Counters Matter", "Lifegain Tribal")
- Alliteration and a little menace both work; puns are fine if they land

Use it as the `# ` heading, the file slug, and the `**Name:**` metadata line, so
the deck is referred to the same way everywhere.

### Charts

Embed the unicode charts directly in the markdown, and link out to the richer
page:

```bash
python3 deckchart.py draft.md --html notes/YYYY-MM-DD-<slug>-charts.html
```

That prints the unicode blocks on stdout — paste them into the markdown — and
writes a standalone HTML page beside it. Link to the page from the markdown:

    [Full charts](YYYY-MM-DD-<slug>-charts.html)

Unicode goes in the markdown because a deck file gets read on a phone through the
Drive connector, where mermaid and images show up as raw text. Block characters
render in every viewer. The HTML page is a companion for reading on a desktop,
never a replacement — the markdown must stand alone.

### The build writes NOTHING until the user says commit

This skill is **read-only against the database, without exception**, for the entire
build. That means:

- Never call `POST /cards/add` or `/cards/remove`, dry run or not
- Never call `POST /decks/create`, `/decks/list` or `/decks/disassemble`
- Never send a write statement to `POST /query`
- Do not even mint an admin token; the whole build needs only open reads

Creating the deck **acquires whatever bulk cannot cover**, so an accidental
`/decks/create` does not just record a deck, it adds cards to their collection.

A finished build is a **proposal**. It produces exactly one artifact: a markdown
file in `notes/`. It consumes no cards, reserves nothing, and does not appear in
`card_usage` or `bulk_cards`.

**The user commits the deck, not the skill.** Only when they explicitly says to commit
it does anything reach the database, and that is a separate action they ask for by
name — never the tail end of a build, never inferred from them liking the list.
If a build seems to call for a database change, stop and ask instead.

## The deck must function, not just score

**Learned the hard way on 2026-09-05.** A build scored 68/100 and was unplayable:
55% of its cards were mana sources, it held 24 creatures, and in fifteen turns of
real play it drew four of them. The rubric had rewarded exactly that — it paid for
ramp count and interaction count and nothing for having a board or a win condition.

`deckcheck.py` and the rubric were fixed (ramp and mana sources now scored against
a target, interaction capped at the best 14, and criterion 5 replaced with Closing
Power). But **do not trust the score alone**. Before any deck is proposed, check
these directly and state them in the writeup:

| Check | Healthy for a creature deck |
|---|---|
| Creatures | 30-35 |
| Creatures at 1-3 mana | 20+ |
| **Lands** (count them separately from ramp) | 36-38 for a ~2.9 CMC deck |
| Total mana sources (lands + ramp) | 44-50 |
| Interaction pieces | 10-15, not 19 |
| Cards that feed the commander's actual trigger | count it explicitly |

**Lands and ramp are not interchangeable.** Ramp does not help you hit your third
land drop and a dork dies to the same wrath as everything else, so never let a
high ramp count justify a low land count. Cutting 37 lands to 34 in one build took
the miss-your-third-drop rate from 13% to 18% and the miss-your-fourth rate to
38%. `deckcheck.py` now scores this as a measured probability, but check the land
count yourself before proposing.

**Verify that "ramp" actually ramps *you*.** `roles_for()` tagged Emergency Eject
as ramp; its text gives the Lander token to the opponent whose permanent it
destroyed. Another card in the same list tapped for mana equal to its own power,
which starts at one. Of thirteen tagged ramp cards in that deck, eight really
accelerated.

And check that the payoff cards do what the grouping claims **by reading the
oracle text**, not by tag or by intent. Real failures caught in one build: a card
granting +0/+1 filed as pump (power never rises, so the commander never triggers);
a creature that pumps only when *blocking*, which can never coincide with dealing
combat damage to a player; an equipment granting shroud, switching off the deck's
own targeted pumps; a card whose animation *sets* base power, so power can never
exceed it.

`python3 test_rubric_rewards_wincon.py` guards the rubric against regressing.

### Three more failures from the same build, worth not repeating

**Ask whether the deck will actually play.** Legality was proven mechanically and
the deck was scored five ways, but nobody asked "how many creatures are on board
by turn five." One real game answered it. Before proposing, state the creature
count, the count at 1-3 mana, and roughly what turn the engine comes online.

**Freeze an artifact while it is being graded.** A grader was midway through
scoring a decklist that changed under it three times, and correctly reported that
its brief no longer matched the file. Finish edits, then spawn the panel.

**Do not trust the collection data for the cards you build around.** Four cards in
one build turned out not to exist physically. The tell was systematic: a card with
`free = 1` whose other copies all sit inside built decks is very likely a phantom
spare credited at build time. Check `card_usage` for that shape on any card the
deck leans on, and say so if the deck depends on one.

## Scoring caveats

- `deckcheck.py` computes criteria 1, 2, 3 and 5 as arithmetic. Trust those.
- **Criterion 4 (synergy) is a tag-derived floor only.** The real criterion is a
  hook graph over actual rules text — a grader must build it and can revise the
  number in either direction. Never report the floor as the final synergy score.
- The rubric currently scores stock precons into bracket 3, so it reads roughly
  15-20 points generous. Until that is recalibrated, treat the **relative**
  score between drafts as the signal and the absolute number as soft.
## Querying the collection

One database, no shards, no schema prefixes — `cards`, `deck_cards`,
`legalities`, `card_search` are all just tables. `GET /schema` lists every one
with its columns and row counts.

The gotchas that matter for a build, in full in the **mtg-api** skill:

- **Filter on `owner`.** Without it a query sums every owner.
- **Colour identity is stored alphabetically** — `'UW'`, never `'WU'`. Sort the
  letters before comparing or an exact match returns nothing. This is the one
  that will bite a colour-identity check.
- **Absence in `legalities` means not legal.** Only legal/banned/restricted are
  stored, so use `NOT EXISTS` and treat NULL as illegal.
- `card_search` is FTS5, `rowid` = `cards.id`, and the table name must be
  unqualified inside `MATCH`.
- Basic lands and tokens are **not in the collection at all**. Do not read
  their absence as them being short on lands.
- Grouping fans out across printings — `GROUP BY owner, name_norm`.

Never record a number a query can answer. Collection sizes, pool depth, deck
counts — state the query instead, because a number written down rots and then
gets believed.
