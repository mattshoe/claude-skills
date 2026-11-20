# Deck architecture

How the user thinks about a Commander deck. Use it as the frame for any judgment about a deck or a card in one. It's knowledge, not a workflow.

## Categories

Every deck breaks down into six categories.
- **Land.** Single-faced lands, utility lands included.
- **Ramp.** Mana rocks, dorks, cost reducers, land untappers and extra land drops.
- **Draw.** Card draw and card advantage.
- **Removal.** Usually targeted. Ideally it hits any permanent type for flexibility, but that's a preference, not a requirement. Burn, destroy, exile, bounce and wipes all count.
- **Protection.** Counterspells, hexproof, shroud, indestructible and anything else that saves your pieces.
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
| Synergy | 26 |
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

- 2026-11-20: Created from the user's baseline, 37 land, 10 ramp, 10 draw, 8 removal, 8 protection, 26 synergy, and the multi-role rule.
