#!/usr/bin/env python3
"""List the combos in a deck from Commander Spellbook, one aggregate call.

Usage: spellbook.py deck.tsv > combos.tsv
Columns: cards (semicolon-separated), produces. Only combos fully in the deck, with 2 or more cards, or 1 card and no
other requirements. Names are matched back to deck.tsv, so double-faced cards keep the deck's spelling.
"""
import csv, json, sys, urllib.request

rows = list(csv.DictReader(open(sys.argv[1]), delimiter='\t'))
names = {r['name'].split(' // ')[0].lower(): r['name'] for r in rows}
body = {'main': [{'card': r['name'].split(' // ')[0], 'quantity': int(r['qty'])} for r in rows if r['role'] != 'commander'],
        'commanders': [{'card': r['name'].split(' // ')[0], 'quantity': 1} for r in rows if r['role'] == 'commander']}
req = urllib.request.Request('https://backend.commanderspellbook.com/find-my-combos', json.dumps(body).encode(),
                             {'Content-Type': 'application/json', 'User-Agent': 'mtg-deck-analyzer/1.0'})
res = json.load(urllib.request.urlopen(req, timeout=120))['results']
print('cards\tproduces')
seen = set()
for c in res['included']:
    cards = [names.get(u['card']['name'].split(' // ')[0].lower()) for u in c['uses']]
    if None in cards or (len(cards) == 1 and (c.get('requires') or c.get('easyPrerequisites') or c.get('notablePrerequisites'))):
        continue
    key = tuple(sorted(cards))
    if key in seen:
        continue
    seen.add(key)
    print('; '.join(key) + '\t' + ', '.join(p['feature']['name'] for p in c['produces'][:3]))
print(f'{len(seen)} combos', file=sys.stderr)
