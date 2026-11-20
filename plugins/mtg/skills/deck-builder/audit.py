#!/usr/bin/env python3
"""Audit a built deck: legality, coloured mana sources, and what it costs to buy.

Usage: audit.py deck.tsv --budget DOLLARS --scope any|collection
Needs ~/.mtg-api.env loaded. deck.tsv comes from deck.py.

Legality: 100 cards, one commander, singleton apart from basics, inside the commander's colour identity, legal in
Commander, every name found on Scryfall.

Mana: Frank Karsten's method for 99-card decks. For each spell, the coloured sources needed so that, having hit your land
drops, you can cast it on the turn equal to its mana value at least (89 + mana value)% of the time. Exact hypergeometric
odds, drawing on turn 1 as multiplayer does, with up to two free mulligans of a 7-card hand outside 2 to 5 lands. Checked
against Karsten's published 99-card figures, 19 sources for C on turn 1 and 30 for CC on turn 2, this gives 20 and 30.
Only lands count as sources. Hybrid and Phyrexian pips need no particular colour.

Cost: one collection query for what's owned, then Scryfall searches of up to 15 names each, cheapest printing first.
A card owned anywhere in the collection costs nothing. One owned but already in other decks is flagged. Basic lands are
never bought. With --scope collection, every card must have a free copy.
"""
import csv, json, os, re, sys, time, urllib.parse, urllib.request
from math import comb

a = sys.argv[1:]
deck_f = a[0]
budget = float(a[a.index('--budget') + 1]) if '--budget' in a else None
scope = a[a.index('--scope') + 1] if '--scope' in a else 'any'
rows = list(csv.DictReader(open(deck_f), delimiter='\t'))
COLORS = 'WUBRG'
BASIC_TYPES = {'plains': 'W', 'island': 'U', 'swamp': 'B', 'mountain': 'R', 'forest': 'G'}
is_land = lambda r: bool(r['type']) and all('Land' in f for f in r['type'].split(' // '))
is_basic = lambda r: 'Basic' in r['type'] and is_land(r)
problems = []

# Legality
total = sum(int(r['qty']) for r in rows)
cmdrs = [r for r in rows if r['role'] == 'commander']
if total != 100:
    problems.append(f'{total} cards, not 100')
if len(cmdrs) != 1:
    problems.append(f'{len(cmdrs)} commanders marked, not 1')
ident = set(cmdrs[0]['identity']) if cmdrs else set(COLORS)
for r in rows:
    if not r['type']:
        problems.append(f'not found on Scryfall: {r["name"]}')
        continue
    if int(r['qty']) > 1 and not is_basic(r) and 'any number of cards named' not in r['text'].lower():
        problems.append(f'{r["qty"]} copies of {r["name"]}')
    if not set(r['identity']) <= ident:
        problems.append(f'outside colour identity: {r["name"]} ({r["identity"]})')
    if r['legal'] != '1':
        problems.append(f'not legal in Commander: {r["name"]}')


# Mana
def prob(S, pips, mv, L, N=99):
    O, X, n = L - S, N - L, 7 + mv
    hands, good, tot7 = {}, 0, comb(N, 7)
    for s in range(min(S, 7) + 1):
        for o in range(min(O, 7 - s) + 1):
            x = 7 - s - o
            if x > X:
                continue
            p = comb(S, s) * comb(O, o) * comb(X, x) / tot7
            hands[(s, o)] = p
            good += p if 2 <= s + o <= 5 else 0
    bad, num, den, k, R = 1 - good, 0, 0, n - 7, N - 7
    for (s, o), p in hands.items():
        w = p * ((1 + bad) if 2 <= s + o <= 5 else 0) + p * bad * bad
        rs, ro, rx = S - s, O - o, X - (7 - s - o)
        for ds in range(min(rs, k) + 1):
            for do in range(min(ro, k - ds) + 1):
                dx = k - ds - do
                if dx > rx:
                    continue
                q = w * comb(rs, ds) * comb(ro, do) * comb(rx, dx) / comb(R, k)
                if s + o + ds + do >= mv:
                    den += q
                    num += q if s + ds >= pips else 0
    return num / den if den else 0


def needed(pips, mv, L):
    mv = max(1, min(mv, 7))
    for S in range(pips, L + 1):
        if prob(S, pips, mv, L) >= (89 + mv) / 100:
            return S
    return L


lands = [r for r in rows if is_land(r)]
L = sum(int(r['qty']) for r in lands)
sources = {c: 0 for c in COLORS}
for r in lands:
    makes = set(r['produces']) & set(COLORS)
    if not makes and re.search(r'search your library for', r['text'], re.I):
        named = {BASIC_TYPES[t] for t in BASIC_TYPES if re.search(r'\b' + t + r'\b', r['text'], re.I)}
        makes = named or ident
    for c in makes & ident:
        sources[c] += int(r['qty'])
need, hardest, cache = {c: 0 for c in COLORS}, {}, {}
for r in rows:
    if is_land(r) or not r['cost']:
        continue
    cost = r['cost'].split(' // ')[0]
    for c in COLORS:
        pips = len(re.findall(r'\{' + c + r'\}', cost))
        if not pips:
            continue
        key = (pips, int(r['mv'] or 0))
        if key not in cache:
            cache[key] = needed(*key, L)
        if cache[key] > need[c]:
            need[c], hardest[c] = cache[key], f'{r["name"]} ({cost})'
for c in COLORS:
    if need[c] > sources[c]:
        problems.append(f'{c} has {sources[c]} sources, {hardest[c]} wants {need[c]}')


# Ownership and price
def api(sql):
    req = urllib.request.Request(os.environ['MTG_API_URL'] + '/query', json.dumps({'sql': sql, 'fmt': 'objects'}).encode(),
                                 {'Content-Type': 'application/json', 'User-Agent': 'mtg-deck-builder/1.0'})
    out = json.load(urllib.request.urlopen(req, timeout=60))
    if isinstance(out, dict) and 'error' in out:
        sys.exit(out['error'])
    return out['rows']


norm = lambda n: n.split(' // ')[0].strip().lower()  # Scryfall's exact-name search wants the front face
full = lambda n: n.strip().lower()  # the collection keys double-faced cards by both faces
names = [r['name'] for r in rows if not is_basic(r) and r['type']]
inlist = ','.join("'" + full(n).replace("'", "''") + "'" for n in names)
owned = {}
for u in api(f"SELECT name_norm, SUM(owned) owned, SUM(free) free FROM card_usage WHERE owner_id = {int(os.environ['MTG_OWNER_ID'])} "
             f"AND name_norm IN ({inlist}) GROUP BY name_norm"):
    owned[u['name_norm']] = (int(u['owned'] or 0), int(u['free'] or 0))
buy = [n for n in names if owned.get(full(n), (0, 0))[0] == 0]
in_decks = [n for n in names if owned.get(full(n), (0, 0))[0] > 0 and owned[full(n)][1] == 0]
if scope == 'collection':
    for n in buy + in_decks:
        problems.append(f'no free copy in the collection: {n}')
price = {}
for i in range(0, len(buy), 15):
    q = '(' + ' or '.join('!"' + norm(n).replace('"', '') + '"' for n in buy[i:i + 15]) + ') prefer:usd-low'
    url = 'https://api.scryfall.com/cards/search?' + urllib.parse.urlencode({'q': q, 'unique': 'cards'})
    while url:
        try:
            page = json.load(urllib.request.urlopen(urllib.request.Request(
                url, headers={'User-Agent': 'mtg-deck-builder/1.0', 'Accept': 'application/json'}), timeout=60))
        except urllib.error.HTTPError as e:
            problems.append(f'Scryfall price search failed ({e.code}) for: ' + ', '.join(buy[i:i + 15]))
            break
        for c in page['data']:
            p = c['prices'].get('usd') or c['prices'].get('usd_foil') or c['prices'].get('usd_etched')
            price[norm(c['name'])] = float(p) if p else None
        url = page.get('next_page')
        time.sleep(0.1)
cost_total = sum(price.get(norm(n)) or 0 for n in buy)
unpriced = [n for n in buy if price.get(norm(n)) is None]
if budget is not None and cost_total > budget:
    problems.append(f'buying costs ${cost_total:.2f}, over the ${budget:.2f} budget by ${cost_total - budget:.2f}')

print('## Problems\n')
print('\n'.join('- ' + p for p in problems) if problems else 'None.')
print(f'\n## Mana, {L} lands\n\n| Colour | Sources | Needed | Hardest spell |\n|---|---|---|---|')
for c in COLORS:
    if c in ident:
        print(f'| {c} | {sources[c]} | {need[c]} | {hardest.get(c, "")} |')
print(f'\n## Cost, scope {scope}\n')
print(f'{len(names) - len(buy)} owned, {len(buy)} to buy for ${cost_total:.2f}' + (f' of a ${budget:.2f} budget' if budget is not None else '') + '.')
if in_decks:
    print('\nOwned but every copy is in another deck: ' + ', '.join(in_decks))
if unpriced:
    print('\nNo price found, counted as $0: ' + ', '.join(unpriced))
if buy:
    print('\n| To buy | Price |\n|---|---|')
    for n in sorted(buy, key=lambda n: -(price.get(norm(n)) or 0)):
        p = price.get(norm(n))
        print(f'| {n} | {"$%.2f" % p if p is not None else "?"} |')
sys.exit(1 if problems else 0)
