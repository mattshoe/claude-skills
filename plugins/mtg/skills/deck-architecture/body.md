# Deck architecture

How the user thinks about a Commander deck. Use it as the frame for any judgment about a deck or a card in one. It's knowledge, not a workflow.

## Probabilities are king

Decks are built around concepts, never around single cards. Every judgment about a deck is aggregate.

- A strong deck has very high synergy across the whole 99. A couple of strong cards don't make it strong.
- One card, however strong, has no meaningful impact on the deck's quality. Neither do 2 or 3 specific cards. The odds of drawing a specific 2 or 3 cards in time to win are so close to zero they may as well be irrelevant.
- Never call a deck good or bad because of one card or a small package. Never say a card makes or breaks a deck, or that adding or cutting one changes its outcome.
- Judge a deck by how many cards serve its concept and its categories, since that's what sets the odds of drawing what it needs on any given turn.
- Judge a card by what it adds to those odds, how many categories it fills and how well it fits the concept, never by its power in a vacuum.
- A combo or bomb counts as one more way to win, weighted by the odds of assembling it. It is never the deck's plan.

## Categories

Every deck breaks down into seven categories.
- **Land.** Single-faced lands, utility lands included.
- **Ramp.** Mana rocks, dorks, cost reducers, land untappers and extra land drops.
- **Draw.** Card draw and card advantage.
- **Removal.** Usually targeted. Ideally it hits any permanent type for flexibility, but that's a preference, not a requirement. Burn, destroy, exile, bounce and wipes all count.
- **Protection.** Counterspells, hexproof, shroud, indestructible and anything else that saves your pieces.
- **Multipliers.** Cards that double or copy what the deck's engine produces, like Doubling Season, Parallel Lives, Panharmonicon, Strionic Resonator, Teysa Karlov or copy effects. They make every other engine piece count twice, so a deck with nothing worth multiplying runs fewer.
- **Synergy.** A bucket that is always broken into its own categories, the pieces of the deck's engine or win con. An aristocrats deck has fodder, sac outlets and payoffs. A go-wide deck has token makers and pumpers.

## Baseline

The starting point for every deck:

| Category | Cards |
|---|---|
| Land | 37 |
| Ramp | 10 |
| Draw | 10 |
| Removal | 8 |
| Protection | 8 |
| Multipliers | 6 |
| Synergy | 20 |
| Total | 99 |

## Tweaks

The baseline moves with the deck. A landfall deck may run more lands. An aristocrats deck may run less protection, since it's naturally hard to interact with. Any move away from the baseline needs a reason tied to how the deck plays. When a deck sits off the baseline, ask whether the deck's plan explains it before calling it a problem.

## Multi-role rule

An ideal deck has most of its cards filling at least 2 categories, for example synergy and removal, or ramp and draw. Each extra role raises the odds of drawing into that category when it's needed.

A card that fills only one category has to earn it by doing its one thing really well. When judging a card, name every category it fills in this deck. A single-role card that's only average at its job is the first candidate to replace, and a replacement that fills the same role plus another is the better pick.

## Standing rules

- Double-faced cards never count as lands, whatever the deck files them as.
- Win plans need redundancy. Payoffs are a category, never one card, unless that card is the commander.

## Related skills

**deck-categories** measures a deck against this, allocating each card to a primary category and listing its other roles. **deck-analyzer** uses both.

## Change log

- 2026-11-20: Added Multipliers at 6, out of Synergy, which drops to 20.
- 2026-11-20: Added Probabilities are king. Decks are built around concepts, judgments are aggregate, single cards and small packages never decide a deck.
- 2026-11-20: Created from the user's baseline, 37 land, 10 ramp, 10 draw, 8 removal, 8 protection, 26 synergy, and the multi-role rule.
