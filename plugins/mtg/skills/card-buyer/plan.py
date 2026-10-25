#!/usr/bin/env python3
"""Plan which local store carts get which cards.

Usage: plan.py < want.txt        (one "QTY Card Name" per line)

Aggregate lookups only, never one request per printing:
- Shopify/BinderPOS stores: ONE search for every wanted card at once
  (title:"A" OR title:"B" ...), paged to the end. Each search page already
  carries every product's variant ids, conditions and prices, so no product
  pages are fetched. Sold-out variants are marked on the page too, stock is
  probed only when a card needs more than one copy.
- StorePass stores: its search has no OR, so one request per card, but each
  reply carries price and stock for every variant, so the store itself gets
  no requests at all.
- Scryfall foil floors: one /cards/collection call per 75 names.

Pass 1 fills non-foil copies store by store in priority order, pass 2 fills
what is still missing with foils in the same order. Within a store, cheapest
qualifying copy first. Prints JSON: per store "cart_items" for /cart/add.js and
the lines it covers, plus "tcgplayer" lines nobody local had.

Read-only. Stock is probed in a throwaway cookie jar, never the user's cart.
"""
import html as htmllib, json, os, re, sys, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

# CARD_STORES="host1,host2" sets the local stores in priority order
STORES = [h.strip() for h in os.environ.get("CARD_STORES", "").split(",") if h.strip()]
if not STORES:
    sys.exit("CARD_STORES is not set, see SKILL.md")
# Stores whose /search page is client-rendered by StorePass: host -> store_id
# CARD_STOREPASS="host=store_id,host=store_id"
STOREPASS = dict(p.strip().split("=", 1) for p in os.environ.get("CARD_STOREPASS", "").split(",") if "=" in p)
CONDITIONS = ["Near Mint", "Lightly Played", "Moderately Played"]
MAX_PAGES = 200
PAGE_SIZE = 10  # BinderPOS search pages hold 10 products
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

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def base_name(title):
    t = title.split(" [")[0].split(" - ")[0].split(" // ")[0]
    return re.sub(r"\s*\([^)]*\)", "", t).strip().lower()

def front(name):
    return name.split(" // ")[0]

def variant(title, cond, vid, price):
    return {"variant_id": int(vid), "title": title, "condition": cond,
            "foil": bool(re.search(r"\bfoil\b", f"{title} {cond}".lower())), "price": price}

def shopify_catalog(host, names):
    """name -> variants, from one combined search paged to the end."""
    q = " OR ".join(f'title:"{front(n)}"' for n in names)
    want = {front(n).lower(): n for n in names}
    out = {n: [] for n in names}
    for page in range(1, MAX_PAGES + 1):
        html = get(f"https://{host}/search?" + urllib.parse.urlencode(
            {"q": q, "type": "product", "page": page}))
        cards = re.split(r'<div class="product-card-list2 ', html)[1:]
        print(f"  {host} page {page}: {len(cards)} products", file=sys.stderr, flush=True)
        if not cards: break
        for c in cards:
            t = re.search(r'grid-view-item__title">([^<]+)<', c)
            if not t: continue
            title = htmllib.unescape(t.group(1)).strip()
            name = want.get(base_name(title))
            if not name or re.search(r"art card|art series|oversized", title.lower()): continue
            conds = {vid: htmllib.unescape(cond).strip() for vid, cond in
                     re.findall(r'<option[^>]*value="(\d+)"[^>]*>([^<]+)<', c)}
            pm = re.search(r"variants='(.*?)'>", c, re.S)
            prices = json.loads(pm.group(1)) if pm else {}
            # The quickview select marks each variant data-available="0|1"
            avail = dict(re.findall(r'value="(\d+)" data-available="(\d)"', c))
            for vid, cond in conds.items():
                if cond.removesuffix(" Foil") in CONDITIONS and vid in prices and avail.get(vid) != "0":
                    x = variant(title, cond, vid, int(prices[vid]["price"]) / 100)
                    if avail.get(vid) == "1": x["in_stock"] = True
                    out[name].append(x)
        if len(cards) < PAGE_SIZE: break  # a short page is the last one
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

def probe_stock(host, variant_id):
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    body = json.dumps({"items": [{"id": variant_id, "quantity": 99}]}).encode()
    req = urllib.request.Request(f"https://{host}/cart/add.js", data=body,
                                 headers={**UA, "Content-Type": "application/json"})
    try: open_url(req, op)
    except urllib.error.HTTPError: pass  # 422 still adds what is in stock
    cart = json.loads(get(f"https://{host}/cart.js", op))
    return sum(i["quantity"] for i in cart["items"] if i["variant_id"] == variant_id)

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
    catalogs = {h: (storepass_catalog if h in STOREPASS else shopify_catalog)(h, names) for h in STORES}
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
                    # Probe only when the page did not say, or more than one copy is needed
                    if "stock" in v: have = v["stock"]
                    elif v.get("in_stock") and need[name] == 1: have = 1
                    else: have = probe_stock(host, v["variant_id"])
                    n = min(need[name], have)
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
