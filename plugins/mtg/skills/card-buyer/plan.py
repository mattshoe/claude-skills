#!/usr/bin/env python3
"""Plan which local store carts get which cards.

Usage: plan.py < want.txt        (one "QTY Card Name" per line)

Aggregate lookups only, never one request per printing:
- Shopify/BinderPOS stores: ONE POST of the whole list to BinderPOS's decklist
  endpoint on portal.binderpos.com. The reply carries every in-stock printing
  with variant ids, conditions, prices and quantities. No paging, no search
  pages, no stock probes. The store itself gets no requests when its
  Shopify.shop id is in CARD_SHOPIFY, otherwise one homepage fetch to read it.
- StorePass stores: its search has no OR, so one request per card, but each
  reply carries price and stock for every variant, so the store itself gets
  no requests at all.
- Scryfall foil floors: one /cards/collection call per 75 names.

Pass 1 fills non-foil copies store by store in priority order, pass 2 fills
what is still missing with foils in the same order. Within a store, cheapest
qualifying copy first. Prints JSON: per store "cart_items" for /cart/add.js and
the lines it covers, plus "tcgplayer" lines nobody local had.

Read-only.
"""
import json, os, re, sys, time, urllib.request, urllib.parse, urllib.error

# CARD_STORES="host1,host2" sets the local stores in priority order
STORES = [h.strip() for h in os.environ.get("CARD_STORES", "").split(",") if h.strip()]
if not STORES:
    sys.exit("CARD_STORES is not set, see SKILL.md")
# Stores whose /search page is client-rendered by StorePass: host -> store_id
# CARD_STOREPASS="host=store_id,host=store_id"
STOREPASS = dict(p.strip().split("=", 1) for p in os.environ.get("CARD_STOREPASS", "").split(",") if "=" in p)
# Shopify.shop ids, which do not always match the hostname: host -> shop
# CARD_SHOPIFY="host=shop.myshopify.com,host=shop.myshopify.com"
SHOPS = dict(p.strip().split("=", 1) for p in os.environ.get("CARD_SHOPIFY", "").split(",") if "=" in p)
CONDITIONS = ["Near Mint", "Lightly Played", "Moderately Played"]
UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json, text/html;q=0.9, */*;q=0.8"}

def open_url(req, opener=None):
    time.sleep(1.0)  # stay polite, the stores throttle bursts
    for attempt in range(6):
        try:
            return (opener or urllib.request.build_opener()).open(req, timeout=30).read().decode()
        except urllib.error.HTTPError as e:
            if (e.code != 429 and e.code < 500) or attempt == 5: raise
            print(f"  retry {attempt + 1}: HTTP {e.code} {req.full_url}", file=sys.stderr, flush=True)
            time.sleep(min(30 * 2 ** attempt, 300))

def get(url, opener=None):
    return open_url(urllib.request.Request(url, headers=UA), opener)

def base_name(title):
    t = title.split(" [")[0].split(" - ")[0].split(" // ")[0]
    return re.sub(r"\s*\([^)]*\)", "", t).strip().lower()

def front(name):
    return name.split(" // ")[0]

def variant(title, cond, vid, price):
    return {"variant_id": int(vid), "title": title, "condition": cond,
            "foil": bool(re.search(r"\bfoil\b", f"{title} {cond}".lower())), "price": price}

def shopify_catalog(host, names, need):
    """name -> in-stock variants, from one POST of the whole list to BinderPOS."""
    shop = SHOPS.get(host)
    if not shop:  # one homepage fetch, set CARD_SHOPIFY to skip it
        m = re.search(r'Shopify\.shop\s*=\s*"([^"]+)"', get(f"https://{host}/"))
        if not m: sys.exit(f"{host}: no Shopify.shop on the homepage")
        shop = m.group(1)
    body = json.dumps([{"card": front(n), "quantity": need[n]} for n in names]).encode()
    url = f"https://portal.binderpos.com/external/shopify/decklist?storeUrl={shop}&type=mtg"
    reply = json.loads(open_url(urllib.request.Request(url, data=body, headers={**UA, "Content-Type": "application/json"})))
    print(f"  {host}: 1 request, {sum(r['found'] for r in reply)} copies across {len(reply)} cards", file=sys.stderr, flush=True)
    want = {front(n).lower(): n for n in names}
    out = {n: [] for n in names}
    for r in reply:
        for p in r["products"] or []:
            title = p["title"]
            name = want.get(base_name(title))
            if not name or re.search(r"art card|art series|oversized", title.lower()): continue
            for v in p["variants"]:
                if v["title"].removesuffix(" Foil") in CONDITIONS and v["quantity"] > 0:
                    out[name].append({**variant(title, v["title"], v["shopifyId"], v["price"]), "stock": v["quantity"]})
    return out

def storepass_catalog(host, names):
    """name -> in-stock variants. StorePass search has no OR, one call per card."""
    out = {}
    for n in names:
        d = json.loads(get(f"https://store.storepass.co/saas/search?store_id={STOREPASS[host]}"
                           f"&limit=100&in_stock=true&q={urllib.parse.quote(front(n))}"))
        vs = []
        for p in d["products"]:
            title = p.get("display_name") or p.get("name") or ""
            # Exact card name only, a handle prefix let Snapdax through for Snap
            if base_name(title) != front(n).lower(): continue
            stock = {i["variant_id"]: i["stock"] for i in (p.get("inventoryTransferInfo") or [])}
            for v in p.get("variant_info") or []:
                if v.get("title", "").removesuffix(" Foil") in CONDITIONS:
                    x = variant(title, v["title"], v["id"], float(v["price"]))
                    x["stock"] = max(0, int(stock.get(v["id"], 0)))  # StorePass can report -1
                    if x["stock"] > 0: vs.append(x)
        out[n] = vs
    return out

def market_floors(names):
    """front name (lower) -> cheapest Scryfall USD, one collection call per 75 names."""
    out, fronts = {}, [front(n) for n in names]
    for i in range(0, len(fronts), 75):  # Scryfall's max per request
        body = json.dumps({"identifiers": [{"name": n} for n in fronts[i:i + 75]]}).encode()
        req = urllib.request.Request("https://api.scryfall.com/cards/collection", data=body,
                                     headers={**UA, "Content-Type": "application/json"})
        for c in json.loads(open_url(req))["data"]:
            ps = [float(c["prices"][k]) for k in ("usd", "usd_foil") if c["prices"].get(k)]
            if ps: out[c["name"].split(" // ")[0].lower()] = min(ps)
    return out

def main():
    need = {}
    for line in sys.stdin:
        m = re.match(r"\s*(?:(\d+)x?\s+)?(.+?)\s*$", line)
        if m and m.group(2): need[m.group(2)] = need.get(m.group(2), 0) + int(m.group(1) or 1)
    names = list(need)
    floors = market_floors(names)
    catalogs = {h: storepass_catalog(h, names) if h in STOREPASS else shopify_catalog(h, names, need) for h in STORES}
    lines = {h: [] for h in STORES}
    for foil in (False, True):
        for host in STORES:
            for name in names:
                floor = floors.get(front(name).lower()) if foil else None
                for v in sorted(catalogs[host][name], key=lambda x: x["price"]):
                    if need[name] <= 0: break
                    if v["foil"] != foil: continue
                    # A local foil fallback must not cost far more than TCGPlayer would.
                    if foil and floor is not None and v["price"] > max(2 * floor, floor + 2): continue
                    n = min(need[name], v["stock"])
                    if n > 0:
                        lines[host].append({**v, "card": name, "qty": n}); need[name] -= n
    out = {"stores": [{"host": h,
                       "cart_items": [{"id": p["variant_id"], "quantity": p["qty"]} for p in lines[h]],
                       "lines": lines[h],
                       "subtotal": round(sum(p["price"] * p["qty"] for p in lines[h]), 2)}
                      for h in STORES],
           "tcgplayer": [f"{q} {n}" for n, q in need.items() if q > 0]}
    print(json.dumps(out, indent=1))

if __name__ == "__main__":
    main()
