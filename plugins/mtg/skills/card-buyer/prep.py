#!/usr/bin/env python3
"""Turn a typed card list into want.txt for plan.py.

Usage: prep.py BOUGHT_FILE < typed.txt > want.txt

Resolves the whole list with one Scryfall /cards/collection call per 75 names,
fuzzy only for names that missed, then drops:
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


def resolve(typed):
    """lowercased name or front face -> card, one call per 75 names."""
    found = {}
    for i in range(0, len(typed), 75):
        body = json.dumps({"identifiers": [{"name": t} for t in typed[i:i + 75]]}).encode()
        req = urllib.request.Request("https://api.scryfall.com/cards/collection", data=body, headers=UA)
        for c in json.load(urllib.request.urlopen(req))["data"]:
            found[c["name"].lower()] = c
            found[c["name"].split(" // ")[0].lower()] = c
        time.sleep(0.15)
    return found


def paper_names(names):
    """Which names have a paper printing. Scryfall hands back one printing per
    name, and that one can be MTGO-only for a card with paper printings too."""
    if not names:
        return set()
    q = "(" + " or ".join('!"%s"' % n for n in names) + ") game:paper"
    d = get("https://api.scryfall.com/cards/search?q=" + urllib.parse.quote(q))
    return {c["name"] for c in d["data"]} if d else set()


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
    parsed = []
    for l in lines:
        m = re.match(r"^(\d+)x?\s+(.+)$", l)
        parsed.append((int(m.group(1)), m.group(2)) if m else (1, l))
    found = resolve([t for _, t in parsed])
    resolved, unknown = [], []
    for qty, typed in parsed:
        d = found.get(typed.lower()) or get("https://api.scryfall.com/cards/named?fuzzy=" + urllib.parse.quote(typed))
        if d:
            resolved.append((qty, d))
        else:
            unknown.append(typed)
    paper = paper_names([d["name"] for _, d in resolved if "paper" not in d.get("games", [])])
    cards, digital = [], []
    for qty, d in resolved:
        name = d["name"].split(" // ")[0] if d.get("layout") in ("transform", "modal_dfc", "adventure", "flip") else d["name"]
        if "paper" in d.get("games", []) or d["name"] in paper:
            cards.append((qty, name))
        else:
            digital.append(name)
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
