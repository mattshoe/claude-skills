#!/usr/bin/env python3
"""Odds of having seen every piece of at least one combo, by turn.

Usage: odds.py combos.json
combos.json:
  {"library": 99,
   "turns": [8, 15],
   "report_turn": 12,
   "extra_draw": {"from_turn": 4, "p": 0.5},
   "combos": {"Niv": [["Niv-Mizzet, Parun"], ["Curiosity", "Ophidian Eye"]], ...}}
Each combo is a list of slots, each slot a list of cards that fill it. A combo is live when every
slot has a different drawn card. Cards can sit in several slots and combos.

Cards seen by turn T = 7 + T (no skipped draw in multiplayer). Extra draw adds Binomial(T - from + 1, p)
cards. Exact method groups cards with the same slot memberships and sums the multivariate
hypergeometric over group counts, then a Monte Carlo cross-checks it.
"""
import itertools, json, random, sys
from math import comb

cfg = json.load(open(sys.argv[1]))
N = cfg.get('library', 99)
t0, t1 = cfg.get('turns', [8, 15])
rt = cfg.get('report_turn', 12)
ex = cfg.get('extra_draw')
combos = cfg['combos']

slots = [(name, i, frozenset(s)) for name, c in combos.items() for i, s in enumerate(c)]
cards = sorted({x for _, _, s in slots for x in s})
sig = {c: frozenset(j for j, (_, _, s) in enumerate(slots) if c in s) for c in cards}
groups = {}
for c, g in sig.items():
    groups.setdefault(g, []).append(c)
glist = list(groups.items())
filler = N - len(cards)
assert filler >= 0, 'more combo cards than library'


def combo_live(name, have):
    """have: dict group-sig -> count drawn. True if each slot of the combo gets its own card."""
    js = [j for j, (n, _, _) in enumerate(slots) if n == name]
    def fill(k, left):
        if k == len(js):
            return True
        for g, n in left.items():
            if n and js[k] in g:
                left[g] -= 1
                if fill(k + 1, left):
                    return True
                left[g] += 1
        return False
    return fill(0, dict(have))


def exact(n, which):
    """P(any combo in `which` is live after seeing n cards)."""
    total = 0
    sizes = [len(c) for _, c in glist]
    for ks in itertools.product(*(range(s + 1) for s in sizes)):
        k = sum(ks)
        if k > n or n - k > filler:
            continue
        have = {g: kk for (g, _), kk in zip(glist, ks)}
        if any(combo_live(w, have) for w in which):
            w = comb(filler, n - k)
            for s, kk in zip(sizes, ks):
                w *= comb(s, kk)
            total += w
    return total / comb(N, n)


def seen(T):
    """List of (cards seen, probability) at turn T."""
    base = 7 + T
    if not ex or T < ex['from_turn']:
        return [(base, 1.0)]
    m, p = T - ex['from_turn'] + 1, ex['p']
    return [(base + k, comb(m, k) * p ** k * (1 - p) ** (m - k)) for k in range(m + 1)]


cache = {}
def P(n, which):
    key = (min(n, N), tuple(which))
    if key not in cache:
        cache[key] = exact(*key)
    return cache[key]


def mc(n, which, trials=200000):
    deck = cards + [None] * filler
    hits = 0
    for _ in range(trials):
        drawn = random.sample(deck, n)
        have = {}
        for c in drawn:
            if c:
                have[sig[c]] = have.get(sig[c], 0) + 1
        hits += any(combo_live(w, have) for w in which)
    return hits / trials


allc = list(combos)
print('turn\tseen\tbase%\textra%' if ex else 'turn\tseen\tbase%')
for T in range(t0, t1 + 1):
    b = P(7 + T, allc)
    row = f'{T}\t{7 + T}\t{100 * b:.2f}'
    if ex:
        row += f"\t{100 * sum(w * P(n, allc) for n, w in seen(T)):.2f}"
    print(row)
print(f'\neach combo alone at turn {rt}, base%' + ('\textra%' if ex else ''))
for c in allc:
    row = f'{c}\t{100 * P(7 + rt, [c]):.2f}'
    if ex:
        row += f"\t{100 * sum(w * P(n, [c]) for n, w in seen(rt)):.2f}"
    print(row)
n = 7 + rt
print(f'\nmonte carlo check, turn {rt} base: exact {100 * P(n, allc):.2f}, simulated {100 * mc(n, allc):.2f}')
