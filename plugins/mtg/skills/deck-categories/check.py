#!/usr/bin/env python3
"""Check an allocation and print the category table.

Usage: check.py deck.tsv alloc.tsv CATEGORY [CATEGORY ...]
alloc.tsv: name<TAB>category<TAB>reason, one row per nonland, noncommander card.
Fails if a card is missing, repeated, unknown, or in a category not listed.
Lands are counted into a Lands row, never allocated. Double-faced cards never count as lands, whatever the deck files them as. The commander is left out.
"""
import csv, sys

deck_f, alloc_f, cats = sys.argv[1], sys.argv[2], sys.argv[3:]
want, lands = {}, 0
for r in csv.DictReader(open(deck_f), delimiter='\t'):
    if r['role'] == 'commander':
        continue
    if ' // ' not in r['type'] and 'Land' in r['type']:
        lands += int(r['qty'])
        continue
    want[r['name']] = int(r['qty'])

got, errors = {}, []
for row in csv.reader(open(alloc_f), delimiter='\t'):
    if not row or row[0] in ('name', ''):
        continue
    name, cat = row[0].strip(), row[1].strip()
    if name in got:
        errors.append(f'repeated: {name}')
    if name not in want:
        errors.append(f'not a nonland card in the deck: {name}')
    if cat not in cats:
        errors.append(f'unknown category {cat!r}: {name}')
    got[name] = cat
for n in want:
    if n not in got:
        errors.append(f'missing: {n}')
if errors:
    print('\n'.join(errors))
    sys.exit(1)

total = sum(want.values()) + lands
print('| Category | Cards |\n|---|---|')
for c in cats:
    print(f'| {c} | {sum(want[n] for n, k in got.items() if k == c)} |')
print(f'| Lands | {lands} |')
print(f'| Total | {total} |')
