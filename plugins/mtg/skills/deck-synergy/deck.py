#!/usr/bin/env python3
"""Print a deck as TSV with oracle text, from the database or a pasted list.

Usage:
  deck.py DECK_KEY_OR_ID > deck.tsv                    (needs ~/.mtg-api.env loaded)
  deck.py --list FILE --commander "NAME" > deck.tsv    (one card per line, "1 Name" or "1x Name (SET) 123")
Prints the deck name to stderr. Columns: qty, name, role, cost, mv, type, game_changer, text.
Double-faced cards join faces with " // ". Scryfall /cards/collection in batches of 75.
"""
import json, os, re, sys, time, urllib.request

UA = {'User-Agent': 'mtg-deck-synergy/1.0', 'Content-Type': 'application/json', 'Accept': 'application/json'}


def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), UA)
    return json.load(urllib.request.urlopen(req, timeout=60))


def from_list(path, commander):
    rows = {}
    for line in open(path):
        line = line.strip()
        if not line or line.startswith('//') or line.startswith('#') or line.endswith(':'):
            continue
        cmdr = '*CMDR*' in line
        line = re.sub(r'\*[A-Z]+\*', '', line).strip()
        m = re.match(r'^(\d+)\s*x?\s+(.+)$', line, re.I)
        qty, name = (int(m.group(1)), m.group(2)) if m else (1, line)
        name = re.sub(r'\s+\([A-Za-z0-9]+\).*$', '', name).strip()
        if name.lower() in ('commander', 'deck', 'sideboard', 'mainboard'):
            continue
        role = 'commander' if cmdr or name.lower() == (commander or '').lower() else 'main'
        if name in rows:
            rows[name]['qty'] += qty
        else:
            rows[name] = {'qty': qty, 'name': name, 'role': role}
    if not any(r['role'] == 'commander' for r in rows.values()):
        sys.exit('no commander found, pass --commander "NAME"')
    return 'pasted list', list(rows.values())


def from_db(arg):
    where, param = ('d.id = ?', int(arg)) if arg.isdigit() else ('d.key = ?', arg)
    res = post(os.environ['MTG_API_URL'] + '/query', {
        'sql': f'SELECT d.name AS deck, dc.qty, dc.name, dc.role FROM deck_cards dc JOIN decks d ON d.id = dc.deck_id WHERE {where} ORDER BY dc.role, dc.name',
        'params': [param], 'fmt': 'objects'})
    if isinstance(res, dict) and 'error' in res:
        sys.exit(res['error'])
    rows = res['rows'] if isinstance(res, dict) and 'rows' in res else res
    if not rows:
        sys.exit(f'no deck {arg}')
    return rows[0]['deck'], rows


a = sys.argv[1:]
if a and a[0] == '--list':
    cmd = a[a.index('--commander') + 1] if '--commander' in a else None
    deck, rows = from_list(a[1], cmd)
else:
    deck, rows = from_db(a[0])
print('DECK ' + deck, file=sys.stderr)

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

print('qty\tname\trole\tcost\tmv\ttype\tgame_changer\ttext')
for r in rows:
    c = oracle.get(r['name'].split(' // ')[0].lower())
    if not c:
        print(f"{r['qty']}\t{r['name']}\t{r['role'] or ''}\t\t\t\t\t")
        continue
    faces = c.get('card_faces') or [c]
    cost = ' // '.join(f.get('mana_cost', '') for f in faces)
    text = ' // '.join(f.get('oracle_text', '').replace('\n', ' | ') for f in faces)
    print(f"{r['qty']}\t{r['name']}\t{r['role'] or ''}\t{cost}\t{int(c.get('cmc', 0))}\t{c['type_line']}\t{int(c.get('game_changer', False))}\t{text}")
