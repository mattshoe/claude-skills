#!/usr/bin/env python3
"""Build a deck's synergy graph from tags, measure it, and score the deck out of 100.

Usage: graph.py deck.tsv tags.tsv "SYNERGY 1" ["SYNERGY 2" ...] [--base Mana=47 Draw=10 Removal=8 Protection=8]
tags.tsv: name<TAB>category<TAB>also<TAB>makes<TAB>uses<TAB>reason<TAB>finds
- also, makes and uses are comma-separated, blank if none. also may hold Elite, a single-role card that does its job exceptionally well.
- Every makes and uses tag carries a strength, dinosaur:3, from 1 weak to 3 strong.
- finds is only for tutors, semicolon-separated: any, a card type (creature, artifact, instant ...), a tag, a card name, or mv=N.
Every nonland card has a row, the commander's category is Commander, lands get a row only when tagged (category Land).
A link joins two cards when one makes a tag the other uses. Each shared tag counts the weaker of its two sides, a pair takes its strongest tag.
Coherence is measured on engine cards, those in a synergy category as primary or also.
One simulation plays 10,000 games: a land a turn, ramp cast cheapest first, the commander cast once there's mana for it,
and each tutor seen fetching the card that links best to what's already there.
"""
import csv, random, re, sys
from collections import defaultdict

a = sys.argv[1:]
base = {'Mana': 47, 'Draw': 10, 'Removal': 8, 'Protection': 8}
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
    faces = r['type'].split(' // ')
    text = r['text'] or ''
    deck[r['name']] = dict(
        qty=int(r['qty']), mv=int(r['mv'] or 0), text=text, type=r['type'].lower(), cmdr=r['role'] == 'commander',
        land=all('Land' in f for f in faces),  # a Pathway is a land, a spell // land card never is
        pitch=bool(re.search(r"rather than pay (this spell's|its) mana cost|from your hand: add", text, re.I)))
    if r['role'] == 'commander':
        commander = r['name']
split = lambda s, sep=',': [t.strip() for t in (s or '').split(sep) if t.strip()]


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
    row += [''] * (7 - len(row))
    name, cat = row[0].strip(), row[1].strip()
    also = split(row[2])
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
        if (c not in cats and c != 'Elite') or c == cat:
            errors.append(f'bad also {c!r}: {name}')
    tags[name] = dict(cat=cat, also=also, makes=strengths(row[3], name), uses=strengths(row[4], name),
                      finds=[f.lower() for f in split(row[6], ';')])
for n, d in deck.items():
    if not d['land'] and n not in tags:
        errors.append(f'missing: {n}')
if errors:
    print('\n'.join(errors))
    sys.exit(1)
for n, d in deck.items():
    if n not in tags:
        tags[n] = dict(cat='Land', also=[], makes={}, uses={}, finds=[])

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
fills = lambda n, c: tags[n]['cat'] == c or c in tags[n]['also']
tutors = sorted(n for n in tags if tags[n]['finds'])


def can_find(tutor, c):
    d = deck[c]
    for f in tags[tutor]['finds']:
        front = d['type'].split(' // ')[0].split()
        if ((f == 'any' and not d['land']) or f in front or f in tags[c]['makes'] or f == c.lower()
                or (f.startswith('mv=') and f[3:].isdigit() and d['mv'] == int(f[3:]) and c != tutor)):
            return True
    return False


# A tutor links at 2 to every engine card it can fetch, since finding them is its job
for tu in tutors:
    for c in tags:
        if c != tu and not deck[c]['land'] and any(fills(c, k) for k in syn) and can_find(tu, c):
            wt[tu][c] = wt[c][tu] = max(wt[tu].get(c, 0), 2)
# The engine cluster only follows links of 2 or more, so a deck of weak links doesn't read as one engine
nbr = defaultdict(set, {x: {y for y, w in d.items() if w >= 2} for x, d in wt.items()})
spells = [n for n in deck if not deck[n]['land'] and not deck[n]['cmdr']]
N = sum(deck[n]['qty'] for n in spells)
engine_cards = {n for n in spells if any(fills(n, c) for c in syn)}
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
hubs = sorted((n for n in tags if not deck[n]['cmdr']), key=lambda n: -len(nbr[n]))[:3]
made = {t for n in tags for t in tags[n]['makes']}
used = {t for n in tags for t in tags[n]['uses']}
# Mana. A permanent's output comes from its "Add" text, sacrificed or non-untapping sources are one-shot
WORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5}


def output(text):
    m = re.search(r'add ((?:\{[^}]+\})+)', text, re.I)
    if m:
        return len(re.findall(r'\{', m.group(1)))
    m = re.search(r'add (one|two|three|four|five) mana', text, re.I)
    return WORDS[m.group(1).lower()] if m else 1


def ramp_kind(n):
    d = deck[n]
    if 'add' not in d['text'].lower():
        if re.search(r'land cards? [^.]*onto the battlefield|put [^.]*lands? [^.]*onto the battlefield|play an additional land', d['text'], re.I):
            return 'later'  # puts a land into play, mana from next turn
        if re.search(r'create [^.]*treasure', d['text'], re.I):
            return 'once'
        return 'none'  # puts a land in hand or ramps conditionally, no simulated mana
    if ('instant' in d['type'] or 'sorcery' in d['type']
            or re.search(r"sacrifice [^:]*: add|doesn't untap|from your hand: add", d['text'], re.I)):
        return 'once'
    return 'later' if 'creature' in d['type'] else 'now'


ramp = {n: (ramp_kind(n), output(deck[n]['text'])) for n in spells if fills(n, 'Ramp')}
land_out = {n: output(deck[n]['text']) for n in deck if deck[n]['land']}
tapped = {n for n in land_out if re.search(r'enters (the battlefield )?tapped', deck[n]['text'], re.I)
          and not re.search(r"tapped unless|if you don't, it enters", deck[n]['text'], re.I)}

library = [n for n, d in deck.items() if not d['cmdr'] for _ in range(d['qty'])]
cmv = deck[commander]['mv']
rng, SIMS = random.Random(1), 10000
mana_at = defaultdict(float)
live, cover = defaultdict(float), defaultdict(float)
for _ in range(SIMS):
    lib = library[:]
    rng.shuffle(lib)
    hand, perm, cast_cmdr = lib[:7], 0, False
    for t in range(1, 8):
        hand.append(lib[6 + t])
        lands = [c for c in hand if deck[c]['land']]
        land = next((c for c in lands if c not in tapped), lands[0] if lands else None)
        new_tapped = 0
        if land:
            hand.remove(land)
            if land in tapped:
                new_tapped = land_out[land]
            else:
                perm += land_out[land]
        pool, later, invested = perm, new_tapped, 0
        # One-shot mana stays in hand for the turn it's needed, so it counts toward this turn's mana without being spent
        held = sum(max(ramp[c][1] - (0 if deck[c]['pitch'] else deck[c]['mv']), 0) for c in hand if c in ramp and ramp[c][0] == 'once')
        for c in sorted((c for c in hand if c in ramp and ramp[c][0] in ('now', 'later')), key=lambda c: deck[c]['mv']):
            cost = 0 if deck[c]['pitch'] else deck[c]['mv']
            if cost > pool:
                continue
            hand.remove(c)
            kind, out = ramp[c]
            pool -= cost
            if kind == 'now':
                pool += out; perm += out
            elif kind == 'once':
                pool += out
            else:
                later += out; invested += cost
        # Mana this turn is what's left for spells, plus what went into ramp that pays off next turn
        if t <= 4:
            mana_at[t] += pool + invested + held
        if not cast_cmdr and pool + invested + held >= cmv:
            cast_cmdr = True
        perm += later
        if t in (3, 5, 7):
            seen = set(lib[:7 + t])
            have = seen | ({commander} if cast_cmdr else set())
            rest = [c for c in lib[7 + t:] if not deck[c]['land']]
            for tu in (c for c in seen if c in tags and tags[c]['finds']):
                best = max((c for c in rest if c not in have and can_find(tu, c)),
                           key=lambda c: sum(wt[c].get(h, 0) for h in have), default=None)
                if best:
                    have.add(best)
            drawn = [n for n in have if n in engine_cards]
            if drawn:
                live[t] += sum(max((wt[n][p] for p in have if p in wt[n] and p != n), default=0) for n in drawn) / len(drawn) / 3
            cover[t] += sum(any(fills(n, c) for n in have) for c in ('Ramp', 'Draw', 'Removal', 'Protection')) / 4
for d in (mana_at, live, cover):
    for k in d:
        d[k] /= SIMS

# Structure and speed. Pitch spells count as costing 1
cost = lambda n: min(deck[n]['mv'], 1) if deck[n]['pitch'] else deck[n]['mv']
nonland = [n for n in tags if not deck[n]['cmdr']]
count = {c: sum(deck[n]['qty'] for n in nonland if fills(n, c)) for c in cats}
lands = sum(d['qty'] for d in deck.values() if d['land'])
have = {'Mana': lands + sum(deck[n]['qty'] for n in spells if fills(n, 'Ramp')), 'Draw': count['Draw'], 'Removal': count['Removal'], 'Protection': count['Protection']}
avg_mv = sum(cost(n) * deck[n]['qty'] for n in spells) / N
cheap = sum(deck[n]['qty'] for n in spells if cost(n) <= 2 and (fills(n, 'Removal') or fills(n, 'Protection')))
n_tutors = sum(deck[n]['qty'] for n in tutors if not deck[n]['cmdr'])

lin = lambda x, lo, hi: max(0.0, min(1.0, (x - lo) / (hi - lo)))
parts = [
    ('Coherence', 'Live synergy at turn 5', 20, lin(live[5] * 3, 1.0, 2.4), f'drawn engine cards average {live[5] * 3:.1f} of 3 on their best live link'),
    ('Coherence', 'Engine share', 10, lin(eng, 0.3, 0.9), f'{eng:.0%} of engine cards in the largest cluster'),
    ('Coherence', 'Multi-role share', 10, lin(multi, 0.2, 0.6), f'{multi:.0%} of spells fill 2+ categories or are Elite'),
] + [('Structure', k, 2.5, min(have[k] / base[k], 1.0), f'{have[k]} of {base[k]}') for k in ('Mana', 'Draw', 'Removal', 'Protection')] + [
    ('Speed', 'Mana on turn 3', 20, lin(mana_at[3], 2.8, 4.6), f'{mana_at[3]:.1f} on average, {mana_at[2]:.1f} on turn 2, {mana_at[4]:.1f} on turn 4'),
    ('Speed', 'Average spell mana value', 10, lin(-avg_mv, -3.5, -1.8), f'{avg_mv:.2f}, pitch spells count as 1'),
    ('Speed', 'Cheap interaction', 10, lin(cheap, 4, 22), f'{cheap} removal or protection at 2 or less'),
    ('Speed', 'Tutors', 10, lin(n_tutors, 1, 10), f'{n_tutors} tutors'),
]
score = sum(w * f for _, _, w, f, _ in parts)

print(f'## Score {score:.0f} / 100\n')
print('| Group | Part | Points | Detail |\n|---|---|---|---|')
for g, p, w, f, d in parts:
    print(f'| {g} | {p} | {w * f:.1f} / {w:g} | {d} |')
print('\n## Draws, tutors fetching\n\n| Turn | Live synergy, of 3 | Core categories in hand |\n|---|---|---|')
for T in (3, 5, 7):
    print(f'| {T} | {live[T] * 3:.1f} | {cover[T]:.0%} |')
print('\n## Categories, primary or also\n\n| Category | Cards |\n|---|---|')
for c in cats:
    print(f'| {c} | {count[c]} |')
print(f'| Lands | {lands} |')
print(f'\n## Hubs\n')
for h in hubs:
    print(f'- {h}: {len(nbr[h])} links of 2 or more, engine share without it {engine(h):.0%}')
print(f'\n## Orphans, {len(orphans)} engine cards with no synergy link\n')
for o in orphans:
    print(f'- {o} ({tags[o]["cat"]})')
print('\n## Dangling tags\n')
print('- Made, nobody uses: ' + (', '.join(sorted(made - used)) or 'none'))
print('- Used, nobody makes: ' + (', '.join(sorted(used - made)) or 'none'))
if tutors:
    print('\n## Tutors\n\n' + ', '.join(f'{t} ({"; ".join(tags[t]["finds"])})' for t in tutors))
