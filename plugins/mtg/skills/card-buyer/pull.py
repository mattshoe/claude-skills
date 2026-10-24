#!/usr/bin/env python3
"""Bulk pull list: one copy of each named card the user owns, as a deck list.

Usage: pull.py [--decks] < names.txt
  default  only cards free in bulk (card_usage.free > 0)
  --decks  every owned card, free or in a deck; stderr says which deck to pull the in-deck ones from
Names may be "QTY Name" or bare, any case. Output is "1 Name" sorted, nothing else.
"""
import os, json, re, sys, urllib.request

UA = {"User-Agent": "mtg-card-buyer/1.0", "Content-Type": "application/json"}
API = os.environ["MTG_API_URL"].rstrip("/") + "/query"
OWNER_ID = int(os.environ["MTG_OWNER_ID"])


def query(sql):
    body = json.dumps({"sql": sql, "fmt": "objects"}).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request(API, data=body, headers=UA)))["rows"]


def sq(s):
    return "'" + s.replace("'", "''") + "'"


decks = "--decks" in sys.argv
names = sorted({re.sub(r"^\d+x?\s+", "", l.strip()).lower() for l in sys.stdin if l.strip()})
rows = []
for i in range(0, len(names), 80):
    lst = ",".join(sq(n) for n in names[i:i + 80])
    cond = "owned > 0" if decks else "free > 0"
    rows += query(f"SELECT name, name_norm, free FROM card_usage WHERE owner_id = {OWNER_ID} AND {cond} AND name_norm IN ({lst})")
print("".join(f"1 {n}\n" for n in sorted({r['name'] for r in rows})), end="")
if decks:
    held = [r["name_norm"] for r in rows if r["free"] <= 0]
    for i in range(0, len(held), 80):
        lst = ",".join(sq(n) for n in held[i:i + 80])
        for r in query(f"SELECT dc.name, group_concat(DISTINCT d.name) decks FROM deck_cards dc JOIN decks d ON d.id = dc.deck_id "
                       f"WHERE d.owner_id = {OWNER_ID} AND COALESCE(d.is_proxy, 0) = 0 AND dc.name_norm IN ({lst}) GROUP BY dc.name_norm"):
            print(f"{r['name']}: {r['decks']}", file=sys.stderr)
