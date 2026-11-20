#!/usr/bin/env python3
"""Simulate how much mana a deck has on each early turn, from its lands and ramp.

Usage: mana.py deck.tsv
Plays 10,000 games: a land a turn, untapped first, then ramp cast cheapest first with what's open. Read from oracle text:
a land is tapped if it enters tapped with no "unless", a source's output is the symbols after "Add", rocks tap the turn they
land, creatures and land fetchers from next turn, rituals and sacrificed or non-untapping sources once. Pitch mana like
Elvish Spirit Guide is free. Mana counted is what's available for spells that turn. The commander isn't cast.
"""
import csv, random, re, sys
from collections import defaultdict

WORDS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5}
rows = list(csv.DictReader(open(sys.argv[1]), delimiter='\t'))
card = {}
for r in rows:
    if r['role'] == 'commander':
        continue
    text, typ = r['text'] or '', r['type']
    land = all('Land' in f for f in typ.split(' // '))
    m = re.search(r'add ((?:\{[^}]+\})+)', text, re.I)
    out = len(re.findall(r'\{', m.group(1))) if m else WORDS.get((re.search(r'add (one|two|three|four|five) mana', text, re.I) or [None, ''])[1].lower(), 1)
    kind = None
    if land:
        kind = 'next' if re.search(r'enters (the battlefield )?tapped', text, re.I) and not re.search(r"tapped unless|if you don't, it enters", text, re.I) else 'now'
    elif re.search(r'\badd \{|\badd (one|two|three|four|five) mana', text, re.I):
        if 'Instant' in typ or 'Sorcery' in typ or re.search(r"sacrifice [^:]*: add|doesn't untap|from your hand: add", text, re.I):
            kind = 'once'
        else:
            kind = 'next' if 'Creature' in typ.split(' // ')[0] else 'now'
    elif re.search(r'land cards? [^.]*onto the battlefield|put [^.]*lands? [^.]*onto the battlefield', text, re.I):
        kind, out = 'next', 1
    pitch = bool(re.search(r'from your hand: add', text, re.I))
    card[r['name']] = dict(land=land, kind=kind, out=out if kind else 0, cost=0 if pitch else int(r.get('mv') or 0), qty=int(r['qty']))

library = [n for n, c in card.items() for _ in range(c['qty'])]
rng, SIMS, TURNS = random.Random(1), 10000, 6
mana, hit = defaultdict(float), defaultdict(float)
for _ in range(SIMS):
    lib = library[:]
    rng.shuffle(lib)
    hand, perm, waking = lib[:7], 0, 0
    for t in range(1, TURNS + 1):
        hand.append(lib[6 + t])
        perm += waking; waking = 0
        lands = [c for c in hand if card[c]['land']]
        land = next((c for c in lands if card[c]['kind'] == 'now'), lands[0] if lands else None)
        if land:
            hand.remove(land)
            if card[land]['kind'] == 'now':
                perm += card[land]['out']
            else:
                waking += card[land]['out']
        pool = perm
        once = sum(max(card[c]['out'] - card[c]['cost'], 0) for c in hand if card[c]['kind'] == 'once')
        for c in sorted((c for c in hand if card[c]['kind'] in ('now', 'next') and not card[c]['land']), key=lambda c: card[c]['cost']):
            if card[c]['cost'] <= pool:
                hand.remove(c); pool -= card[c]['cost']
                if card[c]['kind'] == 'now':
                    perm += card[c]['out']; pool += card[c]['out']
                else:
                    waking += card[c]['out']
        mana[t] += pool + once
        hit[t] += pool + once >= t + 1
print('| Turn | ' + ' | '.join(str(t) for t in range(1, TURNS + 1)) + ' |')
print('|---|' + '---|' * TURNS)
print('| Average mana | ' + ' | '.join(f'{mana[t] / SIMS:.1f}' for t in range(1, TURNS + 1)) + ' |')
print('| Ahead of curve | ' + ' | '.join(f'{hit[t] / SIMS:.0%}' for t in range(1, TURNS + 1)) + ' |')
srcs = sorted(n for n, c in card.items() if c['kind'] and not c['land'])
print(f'\n{len(srcs)} ramp sources read: ' + ', '.join(f"{n} ({card[n]['out']} {card[n]['kind']})" for n in srcs))
