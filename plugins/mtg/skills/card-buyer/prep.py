#!/usr/bin/env python3
"""Turn a typed card list into want.txt for plan.py.

Usage: prep.py BOUGHT_FILE < typed.txt > want.txt

Resolves each name with Scryfall fuzzy, then drops:
- names Scryfall cannot resolve (report them, ask or guess)
- digital-only cards (Alchemy etc, no paper copy)
- cards free in the user's bulk (the API's card_usage.free > 0)
- cards already in BOUGHT_FILE (bought earlier this conversation)
Cards he owns but that are all in decks are kept, they get bought.
Report goes to stderr. Read-only.
"""
import os, json, re, sys, time, urllib.request, urllib.parse, urllib.error

UA = {"User-Agent": "mtg-card-buyer/1.0", "Accept": "application/json", "Content-Type": "application/json"}
API = os.environ["MTG_API_URL"].rstrip("/") + "/query"
OWNER_ID = int(os.environ["MTG_OWNER_ID"])


def get(url):
    for _ in range(4):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA)))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2)
                continue
            return None
    return None


def query(sql):
    body = json.dumps({"sql": sql, "fmt": "objects"}).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request(API, data=body, headers=UA)))["rows"]


def sq(s):
    return "'" + s.replace("'", "''") + "'"


def main():
    bought_file = sys.argv[1]
    try:
        bought = {l.strip().lower() for l in open(bought_file) if l.strip()}
    except FileNotFoundError:
        bought = set()
    lines = [l.strip() for l in sys.stdin if l.strip()]
    cards, unknown, digital = [], [], []
    for l in lines:
        m = re.match(r"^(\d+)x?\s+(.+)$", l)
        qty, typed = (int(m.group(1)), m.group(2)) if m else (1, l)
        d = get("https://api.scryfall.com/cards/named?fuzzy=" + urllib.parse.quote(typed))
        time.sleep(0.15)
        if not d:
            unknown.append(typed)
            continue
        name = d["name"].split(" // ")[0] if d.get("layout") in ("transform", "modal_dfc", "adventure", "flip") else d["name"]
        if "paper" not in d.get("games", []):
            digital.append(name)
            continue
        cards.append((qty, name))
    usage = {}
    names = [n for _, n in cards]
    for i in range(0, len(names), 80):
        lst = ",".join(sq(n.lower()) for n in names[i:i + 80])
        for r in query(f"SELECT name_norm, owned, in_decks, free FROM card_usage WHERE owner_id = {OWNER_ID} AND name_norm IN ({lst})"):
            usage[r["name_norm"]] = r
    free, already, in_decks, out = [], [], [], []
    for qty, n in cards:
        u = usage.get(n.lower())
        if u and u["free"] > 0:
            free.append(n)
        elif n.lower() in bought:
            already.append(n)
        else:
            if u and u["owned"] > 0:
                in_decks.append(n)
            out.append(f"{qty} {n}")
    print("\n".join(out))
    for label, xs in [("UNKNOWN", unknown), ("DIGITAL-ONLY", digital), ("FREE IN BULK", free),
                      ("BOUGHT THIS CONVERSATION", already), ("OWNED BUT ALL IN DECKS (buying)", in_decks)]:
        if xs:
            print(f"{label}: {', '.join(xs)}", file=sys.stderr)
    print(f"TO BUY: {len(out)}", file=sys.stderr)


if __name__ == "__main__":
    main()
