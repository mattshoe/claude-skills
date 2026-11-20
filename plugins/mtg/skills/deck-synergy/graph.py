#!/usr/bin/env python3
"""Build a deck's synergy graph from tags, simulate games, and score the deck against real decks.

Usage: graph.py deck.tsv tags.tsv "SYNERGY 1" ["SYNERGY 2" ...] [--base Mana=47 Draw=10 Removal=8 Protection=8]
                [--reference "DECK NAME" BRACKET]   adds this deck to reference.tsv

tags.tsv columns: name, category, also, makes, uses, reason, finds, mana, modifies
- also, makes and uses are comma-separated. also may hold Elite. makes and uses tags carry a strength, dinosaur:3, 1 to 3.
- finds, tutors only, semicolon-separated: any, a front-face card type, a tag, a card name, or mv=N.
- mana, mana sources only: amount and timing, "2 now", "1 next", "3 once". now taps the turn it lands, next from the
  following turn, once is spent a single time. Lands without a row make 1, tapped lands from next turn.
- modifies: changes to mana output while the card is in play, "mana+1" for every nonland source, "land+1", "all*2".

The simulator knows nothing about specific cards. Each game it plays a land, casts mana sources cheapest first, casts the
commander once it can, and lets each tutor fetch the card that completes the most strong links. The engine is online the
first turn two linked cards are available, each fits one turn's mana and together they fit the mana left over so far.
The engine turn averages that turn for strong links (3) and solid links (2 or more). The score places it among the
reference decks.
"""
import csv, os, random, re, statistics, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'reference.tsv')
a = sys.argv[1:]
record = None
if '--reference' in a:
    i = a.index('--reference')
    record = (a[i + 1], int(a[i + 2]))
    a = a[:i] + a[i + 3:]
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
    text = r['text'] or ''
    deck[r['name']] = dict(
        qty=int(r['qty']), mv=int(r['mv'] or 0), text=text, type=r['type'].lower(), cmdr=r['role'] == 'commander',
        land=all('Land' in f for f in r['type'].split(' // ')),  # a Pathway is a land, a spell // land card never is
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


def mana_spec(s, name):
    if not s.strip():
        return None
    m = re.fullmatch(r'(\d+)\s+(now|next|once)', s.strip().lower())
    if not m:
        errors.append(f'mana must look like "2 now", "1 next" or "3 once": {s!r} on {name}')
        return None
    return int(m.group(1)), m.group(2)


def modifiers(s, name):
    out = []
    for t in split(s):
        m = re.fullmatch(r'(mana|land|all)([+*])(\d+)', t.lower().replace(' ', ''))
        if not m:
            errors.append(f'modifies must look like mana+1, land+1 or all*2: {t!r} on {name}')
            continue
        out.append((m.group(1), m.group(2), int(m.group(3))))
    return out


tags = {}
for row in csv.reader(open(tags_f), delimiter='\t'):
    if not row or row[0] in ('name', ''):
        continue
    row += [''] * (9 - len(row))
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
                      finds=[f.lower() for f in split(row[6], ';')], mana=mana_spec(row[7], name), mods=modifiers(row[8], name))
for n, d in deck.items():
    if not d['land'] and n not in tags:
        errors.append(f'missing: {n}')
if errors:
    print('\n'.join(errors))
    sys.exit(1)
for n, d in deck.items():
    if n not in tags:
        tags[n] = dict(cat='Land', also=[], makes={}, uses={}, finds=[], mana=None, mods=[])
    if d['land'] and not tags[n]['mana']:
        tapped = (re.search(r'enters (the battlefield )?tapped', d['text'], re.I)
                  and not re.search(r"tapped unless|if you don't, it enters", d['text'], re.I))
        tags[n]['mana'] = (1, 'next' if tapped else 'now')

# Graph
fills = lambda n, c: tags[n]['cat'] == c or c in tags[n]['also']
spells = [n for n in deck if not deck[n]['land'] and not deck[n]['cmdr']]
N = sum(deck[n]['qty'] for n in spells)
engine_cards = {n for n in deck if not deck[n]['land'] and any(fills(n, c) for c in syn)}
E = sum(deck[n]['qty'] for n in engine_cards if not deck[n]['cmdr']) or 1


def link(m, u):
    return max((min(m[t], u[t]) for t in m.keys() & u.keys()), default=0)


wt = defaultdict(dict)
names = list(tags)
for i, x in enumerate(names):
    for y in names[i + 1:]:
        w = max(link(tags[x]['makes'], tags[y]['uses']), link(tags[y]['makes'], tags[x]['uses']))
        if w:
            wt[x][y] = wt[y][x] = w
tutors = sorted(n for n in tags if tags[n]['finds'])


def can_find(tutor, c):
    d = deck[c]
    front = d['type'].split(' // ')[0].split()
    for f in tags[tutor]['finds']:
        if ((f == 'any' and not d['land']) or f in front or f in tags[c]['makes'] or f == c.lower()
                or (f.startswith('mv=') and f[3:].isdigit() and d['mv'] == int(f[3:]) and c != tutor)):
            return True
    return False


findable = {tu: {c for c in tags if c != tu and not deck[c]['cmdr'] and can_find(tu, c)} for tu in tutors}
strong = defaultdict(set, {x: {y for y, w in d.items() if w == 3} for x, d in wt.items()})
solid = defaultdict(set, {x: {y for y, w in d.items() if w >= 2} for x, d in wt.items()})
nbr = defaultdict(set, {x: {y for y, w in d.items() if w >= 2} for x, d in wt.items()})
for tu in tutors:  # a tutor holds the engine together by reaching the cards it can fetch
    for c in findable[tu] & engine_cards:
        nbr[tu].add(c); nbr[c].add(tu)


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
        best = max(best, sum(deck[n]['qty'] for n in comp if n in engine_cards and not deck[n]['cmdr']))
    return best / E


cost = lambda n: min(deck[n]['mv'], 1) if deck[n]['pitch'] else deck[n]['mv']
is_src = lambda n, kinds: tags[n]['mana'] is not None and tags[n]['mana'][1] in kinds


def output(n, on):
    amt = tags[n]['mana'][0]
    for m in on:
        for target, op, k in tags[m]['mods']:
            if target == 'all' or (target == 'land') == deck[n]['land']:
                amt = amt + k if op == '+' else amt * k
    return amt


# Simulation
library = [n for n, d in deck.items() if not d['cmdr'] for _ in range(d['qty'])]
SIMS, LAST = 10000, 10
rng = random.Random(1)
online, mana_at = {3: [], 2: []}, defaultdict(float)
for _ in range(SIMS):
    lib = library[:]
    rng.shuffle(lib)
    hand, pos, play, waking = lib[:7], 7, [], []
    cast_cmdr, banked, peak, found = False, 0, 0, {}
    for t in range(1, LAST + 1):
        hand.append(lib[pos]); pos += 1
        play += waking; waking = []
        lands = [c for c in hand if deck[c]['land']]
        land = next((c for c in lands if is_src(c, ('now',))), lands[0] if lands else None)
        if land:
            hand.remove(land)
            (play if is_src(land, ('now',)) else waking).append(land)
        on = play + ([commander] if cast_cmdr else [])
        pool = sum(output(c, on) for c in play)
        once = sum(max(output(c, on) - cost(c), 0) for c in hand if is_src(c, ('once',)))
        made = pool + once
        for c in sorted((c for c in hand if is_src(c, ('now', 'next')) and not deck[c]['land']), key=cost):
            if cost(c) <= pool:
                hand.remove(c); pool -= cost(c)
                if is_src(c, ('now',)):
                    play.append(c); gain = output(c, on + [c]); pool += gain; made += gain
                else:
                    waking.append(c)
        if not cast_cmdr and pool + once >= deck[commander]['mv']:
            cast_cmdr = True; pool -= deck[commander]['mv']
            if pool < 0:
                once += pool; pool = 0
        if t <= 4:
            mana_at[t] += made
        banked += pool
        peak = max(peak, made)
        # Online when two linked cards are available, each fits one turn's mana, and together they fit what's been left over
        avail = {c: cost(c) for c in set(lib[:pos]) if c not in play and c not in waking and c in solid}
        for c in play + waking:
            avail[c] = 0
        avail[commander] = 0 if cast_cmdr else deck[commander]['mv']
        for tu in [c for c in set(lib[:pos]) if c in findable]:
            best = max((c for c in findable[tu] if c not in avail),
                       key=lambda c: (len(strong[c] & avail.keys()), len(solid[c] & avail.keys())), default=None)
            if best and solid[best] & avail.keys():
                avail[best] = cost(best) + cost(tu)
        budget = banked + once
        for level, links in ((3, strong), (2, solid)):
            if level in found:
                continue
            for x, cx in avail.items():
                if cx <= peak and any(y in avail and avail[y] <= peak and cx + avail[y] <= budget for y in links[x]):
                    found[level] = t
                    break
        if 3 in found and t >= 4:  # play on to turn 4 so the mana figures cover every game
            break
    for level in (3, 2):
        online[level].append(found.get(level, LAST + 1))
for t in mana_at:
    mana_at[t] /= SIMS
# The engine turn averages when a strong link comes online and when any solid link does, so a deck without a full engine
# still separates from one with nothing
on3, on2 = statistics.mean(online[3]), statistics.mean(online[2])
avg_online = (on3 + on2) / 2
by = lambda T, level: sum(o <= T for o in online[level]) / SIMS

# Score, placed among the reference decks. Each bracket's median online turn anchors a score.
TARGET = {1: 20, 2: 40, 3: 60, 4: 75, 5: 92}
ref = list(csv.DictReader(open(REF), delimiter='\t')) if os.path.exists(REF) else []
if record:
    ref = [r for r in ref if r['deck'] != record[0]] + [{'deck': record[0], 'bracket': str(record[1]), 'online': f'{avg_online:.2f}'}]
    with open(REF, 'w') as f:
        f.write('deck\tbracket\tonline\n')
        for r in sorted(ref, key=lambda r: float(r['online'])):
            f.write(f"{r['deck']}\t{r['bracket']}\t{r['online']}\n")
med = defaultdict(list)
for r in ref:
    med[int(r['bracket'])].append(float(r['online']))
anchors = sorted([(statistics.median(v), TARGET[b]) for b, v in med.items()] + [(2.0, 100), (LAST + 1.0, 0)])


def place(x):
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 > x0 else y0
    return 100 if x < anchors[0][0] else 0


score = max(0, min(100, place(avg_online)))

# Diagnostics, not scored
lands = sum(d['qty'] for d in deck.values() if d['land'])
count = {c: sum(deck[n]['qty'] for n in tags if not deck[n]['cmdr'] and fills(n, c)) for c in cats}
have = {'Mana': lands + sum(deck[n]['qty'] for n in spells if fills(n, 'Ramp')), 'Draw': count['Draw'],
        'Removal': count['Removal'], 'Protection': count['Protection']}
multi = sum(deck[n]['qty'] for n in spells if tags[n]['also']) / N
avg_mv = sum(cost(n) * deck[n]['qty'] for n in spells) / N
cheap = sum(deck[n]['qty'] for n in spells if cost(n) <= 2 and (fills(n, 'Removal') or fills(n, 'Protection')))
pairs = sum(len(v) for v in strong.values()) // 2
orphans = sorted(n for n in engine_cards if not wt[n] and not deck[n]['cmdr'] and n not in tutors)
hubs = sorted(tags, key=lambda n: -len(strong[n]))[:3]
made_tags = {t for n in tags for t in tags[n]['makes']}
used_tags = {t for n in tags for t in tags[n]['uses']}

print(f'## Score {score:.0f} / 100\n')
print(f'Engine turn {avg_online:.1f}, the average of strong links online on turn {on3:.1f} and solid links on turn {on2:.1f}, never counted as {LAST + 1}. '
      f'Reference decks, {len(ref)}: ' + (', '.join(f'bracket {b} median {statistics.median(v):.1f}' for b, v in sorted(med.items())) or 'none') + '.\n')
print('| Online by turn | 3 | 4 | 5 | 6 | 8 | 10 |\n|---|---|---|---|---|---|---|')
for level, label in ((3, 'Strong link, 3'), (2, 'Solid link, 2 or more')):
    print(f'| {label} | ' + ' | '.join(f'{by(T, level):.0%}' for T in (3, 4, 5, 6, 8, 10)) + ' |')
print('\n## Diagnostics\n\n| Measure | Value |\n|---|---|')
print(f'| Strong links, strength 3 | {pairs} |')
print(f'| Engine share, links of 2 or more | {engine():.0%} |')
print(f'| Multi-role or Elite spells | {multi:.0%} |')
print(f'| Mana made on turns 2, 3, 4 | {mana_at[2]:.1f}, {mana_at[3]:.1f}, {mana_at[4]:.1f} |')
print(f'| Average spell cost, pitch as 1 | {avg_mv:.2f} |')
print(f'| Removal or protection at 2 or less | {cheap} |')
for k in ('Mana', 'Draw', 'Removal', 'Protection'):
    print(f'| {k} against baseline | {have[k]} of {base[k]} |')
print('\n## Categories, primary or also\n\n| Category | Cards |\n|---|---|')
for c in cats:
    print(f'| {c} | {count[c]} |')
print(f'| Lands | {lands} |')
print('\n## Hubs, most strong links\n')
for h in hubs:
    print(f'- {h}: strong links {len(strong[h])}, engine share without it {engine(h):.0%}')
print(f'\n## Orphans, {len(orphans)} engine cards with no link\n')
for o in orphans:
    print(f'- {o} ({tags[o]["cat"]})')
print('\n## Dangling tags\n')
print('- Made, nobody uses: ' + (', '.join(sorted(made_tags - used_tags)) or 'none'))
print('- Used, nobody makes: ' + (', '.join(sorted(used_tags - made_tags)) or 'none'))
if tutors:
    print('\n## Tutors\n\n' + ', '.join(f'{t} ({len(findable[t])} targets)' for t in tutors))
if record:
    print(f'\nAdded to reference.tsv as {record[0]}, bracket {record[1]}.')
