#!/usr/bin/env python3
"""Print a deck as TSV with oracle text, for reading and for subagent briefs.

Usage: deck.py DECK_KEY_OR_ID > deck.tsv
Columns: qty, name, role, cost, type, game_changer, text. Double-faced cards join faces with " // ".
One deck query, then Scryfall /cards/collection in batches of 75. Needs ~/.mtg-api.env loaded.
"""
import json, os, sys, time, urllib.request

UA = {'User-Agent': 'mtg-deck-analyzer/1.0', 'Content-Type': 'application/json', 'Accept': 'application/json'}


def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), UA)
    return json.load(urllib.request.urlopen(req, timeout=60))


arg = sys.argv[1]
where, param = ('d.id = ?', int(arg)) if arg.isdigit() else ('d.key = ?', arg)
res = post(os.environ['MTG_API_URL'] + '/query', {
    'sql': f'SELECT dc.qty, dc.name, dc.role FROM deck_cards dc JOIN decks d ON d.id = dc.deck_id WHERE {where} ORDER BY dc.role, dc.name',
    'params': [param], 'fmt': 'objects'})
rows = res['rows'] if isinstance(res, dict) and 'rows' in res else res
if isinstance(res, dict) and 'error' in res:
    sys.exit(res['error'])
if not rows:
    sys.exit(f'no deck {arg}')

oracle = {}
names = sorted({r['name'].split(' // ')[0] for r in rows})
for i in range(0, len(names), 75):
    got = post('https://api.scryfall.com/cards/collection', {'identifiers': [{'name': n} for n in names[i:i + 75]]})
    for c in got['data']:
        faces = c.get('card_faces') or [c]
        oracle[c['name'].lower()] = c
        oracle[faces[0]['name'].lower()] = c
    for nf in got.get('not_found', []):
        print('NOT FOUND ' + nf.get('name', ''), file=sys.stderr)
    time.sleep(0.1)

print('qty\tname\trole\tcost\ttype\tgame_changer\ttext')
for r in rows:
    c = oracle.get(r['name'].split(' // ')[0].lower())
    if not c:
        print(f"{r['qty']}\t{r['name']}\t{r['role'] or ''}\t\t\t\t", flush=True)
        continue
    faces = c.get('card_faces') or [c]
    cost = ' // '.join(f.get('mana_cost', '') for f in faces)
    text = ' // '.join(f.get('oracle_text', '').replace('\n', ' | ') for f in faces)
    print(f"{r['qty']}\t{r['name']}\t{r['role'] or ''}\t{cost}\t{c['type_line']}\t{int(c.get('game_changer', False))}\t{text}")
