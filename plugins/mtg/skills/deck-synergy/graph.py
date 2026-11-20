#!/usr/bin/env python3
"""Build a deck's synergy graph from tags, measure it, and score the deck out of 100.

Usage: graph.py deck.tsv tags.tsv "SYNERGY 1" ["SYNERGY 2" ...] [--base Mana=47 Draw=10 Removal=8 Protection=8]
tags.tsv: name<TAB>category<TAB>also<TAB>makes<TAB>uses<TAB>reason. also, makes and uses are comma-separated, blank if none.
Every makes and uses tag carries a strength, dinosaur:3, from 1 weak to 3 strong.
An edge's weight is the stronger of its shared tags, each tag counting the weaker of its make and use sides.
Every nonland card has a row, the commander's category is Commander, lands only get a row when tagged (category Land).
Coherence is measured on engine cards, those in a synergy category as primary or also. Plain ramp, draw and removal don't count against it.
An edge joins two cards when one makes a tag the other uses. The commander is always in hand.
"""
import csv, random, re, sys
from collections import defaultdict

a = sys.argv[1:]
base = {'Mana': 47, 'Draw': 10, 'Removal': 8, 'Protection': 8, 'Synergy': 26}
if '--base' in a:
    i = a.index('--base')
    for kv in a[i + 1:]:
        k, v = kv.split('=')
        base[k] = int(v)
    a = a[:i]
deck_f, tags_f, syn = a[0], a[1], a[2:]
cats = ['Ramp', 'Draw', 'Removal', 'Protection'] + syn

deck, commander, errors = {}, None, []
for r in csv.DictReader(open(deck_f), delimiter='\t'):
    land = ' // ' not in r['type'] and 'Land' in r['type']
    deck[r['name']] = dict(qty=int(r['qty']), land=land, mv=int(r['mv'] or 0), text=r['text'], cmdr=r['role'] == 'commander')
    if r['role'] == 'commander':
        commander = r['name']

split = lambda s: [t.strip() for t in (s or '').split(',') if t.strip()]


def strengths(s, name):
    out = {}
    for t in split(s):
        tag, _, w = t.lower().partition(':')
        if w not in ('1', '2', '3'):
            errors.append(f'needs a strength of 1, 2 or 3: {t} on {name}')
            w = '2'
        out[tag.strip()] = int(w)
    return out

tags = {}
for row in csv.reader(open(tags_f), delimiter='\t'):
    if not row or row[0] in ('name', ''):
        continue
    row += [''] * (6 - len(row))
    name, cat = row[0].strip(), row[1].strip()
    also = split(row[2])
    makes, uses = strengths(row[3], name), strengths(row[4], name)
    d = deck.get(name)
    if name in tags:
        errors.append(f'repeated: {name}')
    if not d:
        errors.append(f'not in the deck: {name}')
        continue
    ok = ['Commander'] if d['cmdr'] else ['Land'] if d['land'] else cats
    if cat not in ok:
        errors.append(f'category {cat!r} not allowed for {name}, use one of {ok}')
    for c in also:
        if c not in cats or c == cat:
            errors.append(f'bad also {c!r}: {name}')
    tags[name] = dict(cat=cat, also=also, makes=makes, uses=uses)
for n, d in deck.items():
    if not d['land'] and n not in tags:
        errors.append(f'missing: {n}')
if errors:
    print('\n'.join(errors))
    sys.exit(1)

# Graph
def link(m, u):
    return max((min(m[t], u[t]) for t in m.keys() & u.keys()), default=0)


wt = defaultdict(dict)
names = list(tags)
for i, x in enumerate(names):
    for y in names[i + 1:]:
        w = max(link(tags[x]['makes'], tags[y]['uses']), link(tags[y]['makes'], tags[x]['uses']))
        if w:
            wt[x][y] = wt[y][x] = w
# The engine cluster only follows solid and strong links, so a deck of weak links doesn't read as one engine
nbr = defaultdict(set, {x: {y for y, w in d.items() if w >= 2} for x, d in wt.items()})
spells = [n for n in tags if not deck[n]['land'] and not deck[n]['cmdr']]
N = sum(deck[n]['qty'] for n in spells)
# Coherence is measured on the engine, the cards in a synergy category as primary or also
engine_cards = [n for n in spells if tags[n]['cat'] in syn or set(tags[n]['also']) & set(syn)]
E = sum(deck[n]['qty'] for n in engine_cards) or 1


def engine(skip=None):
    seen, best = set(), 0
    for s in tags:
        if s in seen or s == skip:
            continue
        comp, stack = set(), [s]
        while stack:
            x = stack.pop()
            if x in comp or x == skip:
                continue
            comp.add(x)
            stack.extend(nbr[x] - comp)
        seen |= comp
        best = max(best, sum(deck[n]['qty'] for n in comp if n in engine_cards))
    return best / E


eng = engine()
orphans = sorted(n for n in engine_cards if not wt[n])
multi = sum(deck[n]['qty'] for n in spells if tags[n]['also']) / N
hubs = sorted((n for n in tags if not deck[n]['cmdr']), key=lambda n: -sum(wt[n].values()))[:3]
made = {t for n in tags for t in tags[n]['makes']}
used = {t for n in tags for t in tags[n]['uses']}

# Draw simulation, cards seen by turn T = 7 + T
library = [n for n, d in deck.items() if not d['cmdr'] for _ in range(d['qty'])]
fills = lambda n, c: n in tags and (tags[n]['cat'] == c or c in tags[n]['also'])
rng, SIMS, live = random.Random(1), 20000, {}
for T in (3, 5, 7):
    tot_share = tot_cov = 0
    for _ in range(SIMS):
        hand = set(rng.sample(library, 7 + T))
        drawn = [n for n in hand if n in engine_cards]
        have = hand | {commander}
        if drawn:
            tot_share += sum(max((wt[n][p] for p in have if p in wt[n]), default=0) for n in drawn) / len(drawn) / 3
        tot_cov += sum(any(fills(n, c) for n in hand) for c in ('Ramp', 'Draw', 'Removal', 'Protection')) / 4
    live[T] = (tot_share / SIMS, tot_cov / SIMS)

# Structure and speed
lands = sum(d['qty'] for d in deck.values() if d['land'])
count = {c: sum(deck[n]['qty'] for n in spells if fills(n, c)) for c in cats}
have = {'Mana': lands + count['Ramp'], 'Draw': count['Draw'], 'Removal': count['Removal'], 'Protection': count['Protection'], 'Synergy': E}
avg_mv = sum(deck[n]['mv'] * deck[n]['qty'] for n in spells) / N
cheap = sum(deck[n]['qty'] for n in spells if deck[n]['mv'] <= 2 and (fills(n, 'Removal') or fills(n, 'Protection')))

# Mana simulation. One land a turn, ramp cast cheapest first with what's open, adding a mana next turn, 2 for {C}{C} rocks
gain = {n: 2 if '{C}{C}' in deck[n]['text'] else 1 for n in spells if fills(n, 'Ramp')}
MSIMS, mana_at = 20000, {2: 0, 3: 0, 4: 0}
for _ in range(MSIMS):
    lib = library[:]
    rng.shuffle(lib)
    hand, pos, lands_out, ramp_out = lib[:7], 7, 0, 0
    for t in range(1, 5):
        hand.append(lib[pos]); pos += 1
        land = next((c for c in hand if deck[c]['land']), None)
        if land:
            hand.remove(land); lands_out += 1
        open_mana = lands_out + ramp_out
        if t in mana_at:
            mana_at[t] += open_mana
        for c in sorted((c for c in hand if c in gain), key=lambda c: deck[c]['mv']):
            if deck[c]['mv'] <= open_mana:
                open_mana -= deck[c]['mv']; ramp_out += gain[c]; hand.remove(c)
mana_at = {t: v / MSIMS for t, v in mana_at.items()}
land_word = r'\b(land|lands|basic|forest|island|swamp|mountain|plains)\b'
tutor = sorted(n for n in spells if re.search(r'search your library for', deck[n]['text'], re.I)
               and not re.search(r'search your library for [^.|]*?' + land_word, deck[n]['text'], re.I))

lin = lambda x, lo, hi: max(0.0, min(1.0, (x - lo) / (hi - lo)))
parts = [
    ('Coherence', 'Live synergy at turn 5', 20, lin(live[5][0], 0.3, 0.9), f'drawn engine cards average {live[5][0] * 3:.1f} of 3 on their best live link'),
    ('Coherence', 'Engine share', 10, lin(eng, 0.3, 0.9), f'{eng:.0%} of engine cards in the largest cluster'),
    ('Coherence', 'Multi-role share', 10, lin(multi, 0.2, 0.7), f'{multi:.0%} of spells fill 2+ categories'),
] + [('Structure', k, 4, min(have[k] / base[k], 1.0), f'{have[k]} of {base[k]}') for k in ('Mana', 'Draw', 'Removal', 'Protection', 'Synergy')] + [
    ('Speed', 'Mana on turn 4', 15, lin(mana_at[4], 4.0, 6.5), f'{mana_at[4]:.1f} on average, {mana_at[2]:.1f} on turn 2, {mana_at[3]:.1f} on turn 3'),
    ('Speed', 'Average spell mana value', 10, lin(-avg_mv, -4.0, -2.0), f'{avg_mv:.2f}'),
    ('Speed', 'Cheap interaction', 8, lin(cheap, 0, 20), f'{cheap} removal or protection at 2 or less'),
    ('Speed', 'Tutors', 7, lin(len(tutor), 0, 8), f'{len(tutor)} nonland tutors'),
]
score = sum(w * f for _, _, w, f, _ in parts)

print(f'## Score {score:.0f} / 100\n')
print('| Group | Part | Points | Detail |\n|---|---|---|---|')
for g, p, w, f, d in parts:
    print(f'| {g} | {p} | {w * f:.1f} / {w} | {d} |')
print('\n## Draws\n\n| Turn | Live synergy, of 3 | Core categories in hand |\n|---|---|---|')
for T, (s, c) in live.items():
    print(f'| {T} | {s * 3:.1f} | {c:.0%} |')
print('\n## Categories, primary or also\n\n| Category | Cards |\n|---|---|')
for c in cats:
    print(f'| {c} | {count[c]} |')
print(f'| Lands | {lands} |')
print(f'\n## Hubs\n')
for h in hubs:
    print(f'- {h}: {len(wt[h])} links, weight {sum(wt[h].values())}, engine share without it {engine(h):.0%}')
print(f'\n## Orphans, {len(orphans)} engine cards with no synergy link\n')
for o in orphans:
    print(f'- {o} ({tags[o]["cat"]})')
print('\n## Dangling tags\n')
print('- Made, nobody uses: ' + (', '.join(sorted(made - used)) or 'none'))
print('- Used, nobody makes: ' + (', '.join(sorted(used - made)) or 'none'))
if tutor:
    print('\n## Tutors\n\n' + ', '.join(tutor))
