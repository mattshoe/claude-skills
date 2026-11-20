#!/usr/bin/env python3
"""Turn a decklist into TSV with everything the build needs, from one Scryfall pass.

Usage: deck.py list.txt > deck.tsv
list.txt is one card per line, "1 Name" or "Name", with the commander marked *CMDR*.
Columns: qty, name, role, cost, mv, type, identity, produces, legal, text.
identity and produces are colour letters, legal is 1 when the card is legal in Commander.
Scryfall /cards/collection in batches of 75. NOT FOUND names go to stderr.
"""
import json, re, sys, time, urllib.request

UA = {'User-Agent': 'mtg-deck-builder/1.0', 'Content-Type': 'application/json', 'Accept': 'application/json'}
rows = {}
for line in open(sys.argv[1]):
    line = line.strip()
    if not line or line.startswith('#') or line.endswith(':'):
        continue
    cmdr = '*CMDR*' in line
    line = re.sub(r'\*[A-Z]+\*', '', line).strip()
    m = re.match(r'^(\d+)\s*x?\s+(.+)$', line, re.I)
    qty, name = (int(m.group(1)), m.group(2)) if m else (1, line)
    name = re.sub(r'\s+\([A-Za-z0-9]+\).*$', '', name).strip()
    r = rows.setdefault(name, {'qty': 0, 'name': name, 'role': 'main'})
    r['qty'] += qty
    if cmdr:
        r['role'] = 'commander'

cards = {}
names = sorted({n.split(' // ')[0] for n in rows})
for i in range(0, len(names), 75):
    req = urllib.request.Request('https://api.scryfall.com/cards/collection',
                                 json.dumps({'identifiers': [{'name': n} for n in names[i:i + 75]]}).encode(), UA)
    got = json.load(urllib.request.urlopen(req, timeout=60))
    for c in got['data']:
        cards[c['name'].lower()] = c
        cards[(c.get('card_faces') or [c])[0]['name'].lower()] = c
    for nf in got.get('not_found', []):
        print('NOT FOUND ' + nf.get('name', ''), file=sys.stderr)
    time.sleep(0.1)

print('qty\tname\trole\tcost\tmv\ttype\tidentity\tproduces\tlegal\ttext')
for r in rows.values():
    c = cards.get(r['name'].split(' // ')[0].lower())
    if not c:
        print(f"{r['qty']}\t{r['name']}\t{r['role']}\t\t\t\t\t\t0\t")
        continue
    faces = c.get('card_faces') or [c]
    cost = ' // '.join(f.get('mana_cost', '') for f in faces)
    text = ' // '.join(f.get('oracle_text', '').replace('\n', ' | ') for f in faces)
    legal = int(c.get('legalities', {}).get('commander') == 'legal')
    print(f"{r['qty']}\t{c['name']}\t{r['role']}\t{cost}\t{int(c.get('cmc', 0))}\t{c['type_line']}\t"
          f"{''.join(c.get('color_identity', []))}\t{''.join(c.get('produced_mana', []))}\t{legal}\t{text}")
