---
name: card-buyer
description: Requisition Magic the Gathering cards by adding them to the user's online carts at their local game stores in priority order (from CARD_STORES), then TCGPlayer for whatever is left. Use whenever they give a list of cards to buy, pick up, order, requisition or "put in my cart". Adds to carts only, never checks out or pays.
---

# Card Buyer

Fill the user's carts from a card list. Cart only. Never click checkout, never pay, never enter payment or login details. If a store needs a login to add to cart, stop and tell them.

## Rules

- Priority: the stores in `CARD_STORES`, in order, then TCGPlayer. Each store gets only what earlier stores could not fill. A card can split across stores.
- Conditions: Near Mint, Lightly Played or Moderately Played. Never Heavily Played or Damaged.
- Foil: non-foil first, foil only when no local store has a non-foil copy left, and only if the foil costs at most max(2x, +$2) over the cheapest Scryfall price for any printing. Otherwise the card goes to TCGPlayer.
- Cheapest printing always. Any set, any art, the cheapest qualifying copy wins. `plan.py` sorts every printing a store has by price.
- TCGPlayer: always prefer TCGplayer Direct. After Mass Entry, run the Cart Optimizer and select its TCGplayer Direct cart. Only use a non-Direct seller when no Direct copy exists, and flag it.
- Sanity check on pricey local lines: for any local line over $50, look up the TCGPlayer price (search API below). Keep the local copy unless TCGPlayer is cheaper, then send it there. (A $243 SDCC foil Liliana was the cheapest local copy once, TCGPlayer had it for $6.65. The Soul Stone was $67.75 local vs $77.35 TCGPlayer, local wins.)
- Input is "QTY Card Name" per line. If they give names without quantities, use 1.

## Stores

Config, in `~/.mtg-api.env` (see the mtg-api skill), loaded with `set -a; . ~/.mtg-api.env; set +a` before running any script:

| Var | What |
|---|---|
| `CARD_STORES` | local store hosts in priority order, comma separated, e.g. `shop-a.example.com,shop-b.example.com` |
| `CARD_STOREPASS` | optional, stores whose `/search` page is client-rendered by StorePass, `host=store_id,host=store_id` |
| `MTG_API_URL`, `MTG_OWNER_ID` | the collection, for the bulk checks |

If `CARD_STORES` is missing, stop and ask for the user's stores. Local stores are searched with Shopify `/search?q=` HTML, paged, or the StorePass API for hosts in `CARD_STOREPASS`. Leftovers go to TCGPlayer through the Mass Entry page in Chrome.

Local stores are Shopify + BinderPOS. Product variants are conditions (`Near Mint`, `Lightly Played Foil`, ...). Product type `MTG Single`.

## Workflow

0. The user pastes typed names. Write them to `$SCRATCH/typed.txt` as given and run
   `python3 <skill base directory>/prep.py $SCRATCH/bought.txt < typed.txt > want.txt 2> prep.log`.
   It resolves names with Scryfall fuzzy and drops, reporting each on stderr:
   - UNKNOWN, Scryfall could not resolve it. Guess the closest real card (`Fear of lost life` was Fear of Lost Teeth), add it to want.txt, and say so in the report.
   - DIGITAL-ONLY, Alchemy and other cards with no paper copy. TCGPlayer Mass Entry fails the whole list on one of these.
   - FREE IN BULK, `card_usage.free > 0` for owner_id $MTG_OWNER_ID. They pull these from bulk instead.
   - BOUGHT THIS CONVERSATION, already in `$SCRATCH/bought.txt`.
   Cards they own but that are all in decks are kept and bought. Always filter `owner_id = 1`, never `owner = '$MTG_OWNER'`, some rows have a null owner.
1. If UNKNOWN guesses were added, fix want.txt by hand.
2. Run (optionally with `CARD_STORES=<host>,<host>` to change store order for one run) `python3 <skill base directory>/plan.py < want.txt > plan.json` (about 20s per card, run in background for long lists). It is read-only. It does the whole local chain: non-foil pass through every local store, then foil pass for what is left. Stock is probed in a throwaway cookie jar, never the user's cart. Output: per store `cart_items`, `lines`, `subtotal`, and `tcgplayer` (lines nobody local had).
3. Add to carts in Chrome (the user's real browser, so the cart is their). Load the claude-in-chrome skill first. For each store with non-empty `cart_items`:
   - Navigate a tab to `https://<host>/`.
   - Run in the page with javascript_tool, CART_ITEMS from plan.json:
     ```js
     const r = await fetch('/cart/add.js', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({items: CART_ITEMS})});
     const c = await fetch('/cart.js').then(r => r.json());
     ({status: r.status, items: c.items.map(i => [i.title, i.quantity])})
     ```
   - Check the cart shows each item at the planned quantity. A 422 "Only N items were added" means stock moved, push the shortfall to TCGPlayer.
   - Navigate the tab to `/cart` so the user can review, as a separate step. Never set `location.href` inside the add script, it can kill the fetch.
4. TCGPlayer, for the `tcgplayer` lines plus any shortfall:
   - Navigate to `https://www.tcgplayer.com/massentry?productline=Magic&c=<list>` where `<list>` is URL-encoded lines like `1 Sol Ring` joined by `||`.
   - Check the parsed list on the page. Item Options checkboxes (Printing, Condition) should be Normal+Foil, NM+LP+MP, which was the default for the user's account.
   - Click the main Add to Cart under the item list. An Item Options dialog opens, click its Add to Cart too. If clicking the dialog button by ref does nothing, click it in JS: `[...document.querySelectorAll('button')].filter(b=>b.innerText.trim()==='Add to Cart')[1].click()`.
   - The user shops TCGPlayer themselves too. Never remove cart items you did not add. Page lands on /cart. Do not open checkout.
   - Mass Entry picks the cheapest copy from any seller. Fix that with TCGPlayer's Cart Optimizer, which can rebuild the whole cart as TCGplayer Direct:
     - Navigate to `https://www.tcgplayer.com/cart/optimizer` (or click Optimize under Cart Summary on /cart). Wake the tab first if hidden.
     - Basic Rules toggles: Keep Current Printings ON (default, stops foil swaps), Keep Current Conditions ON (stops HP/Damaged), Keep Current Sellers OFF, Set/Series OFF, Rarities OFF. Click the toggles with the computer tool by ref from `find`, JS clicks do not stick.
     - Click Optimize. Three carts appear: TCGplayer Direct, Verified Sellers, Any Seller, plus Current Cart.
     - Check the TCGplayer Direct cart's Items count equals the current cart's. If it does, click its "Select this cart". If it has fewer items, some cards have no Direct copy: select it anyway only if the dropped cards can be re-added, otherwise keep the current cart and flag the non-Direct lines.
     - It optimizes the whole cart, including items the user added themselves. That is fine, Direct is their rule for everything on TCGPlayer.
     - Verified 2026-10-16: the optimizer page and its three carts. "Select this cart" not yet clicked by the skill, confirm the cart afterward with the check script below.
   - Check the cart after every Mass Entry with this, in the tcgplayer tab, NAMES the cards just added:
     ```js
     const secs=document.body.innerText.split('Save all items');
     NAMES.map(n=>{const s=secs.find(x=>x.includes(n+'\n')); if(!s) return n+': MISSING';
       const i=s.indexOf(n+'\n'); const sh=(s.match(/Shipping\n(\$[\d.]+|FREE)/)||[])[1];
       return n+' | '+(s.includes('TCGplayer Direct')?'DIRECT':s.slice(0,40).replace(/\n/g,' '))+' | ship '+sh+' | '+s.slice(i,i+90).replace(/\n/g,' ')})
     ```
     MISSING usually means the cart spells it differently (Bartolomé shows as Bartolome), search the text before assuming it failed. Report every non-Direct line with its seller and shipping. Remove any line priced far above market (a $28 foil Necropede when non-foil was $0.15), using the JS Remove click from the change log.
   - If the cart shows "Hmm, that's not right / having some trouble on our end", TCGPlayer's cart service is down. Stop and tell the user, retry later.
   - If anything did not match, report it.
   - TCGPlayer is a JS app that does not mount while the tab is hidden. If screenshots are blank or `document.visibilityState` is `hidden`, first left_click a blank spot on the page with the computer tool, that wakes it (verified 2026-10-09). Only ask the user if that fails. The local stores do not care, their cart step is plain fetch.
5. Leave the store tabs open on their cart pages so the user can review. Report per store what went in and the subtotal, plus anything nobody had.
   - Always give a cart permalink for each local store: `https://<host>/cart/<variant_id>:<qty>,<variant_id>:<qty>` built from `cart_items`. It loads the items into a checkout in any browser or device. The user could not see a cart the automation tab clearly had, and the permalink fixed it. Nothing is bought until they pay.

6. Append every bought name to `$SCRATCH/bought.txt`, one per line, so the next list in the same conversation skips them.

## Bulk pull list

When the user asks what to pull from bulk for the cards discussed, gather every name from this conversation (typed lists, want files, bought.txt) and run
`python3 <skill base directory>/pull.py < names.txt`. Add `--decks` when they want cards that are in other decks too, stderr then says which deck holds each one.
Output is a plain deck list, `1 Name` per line, one copy each, sorted. Give them only the deck list in a code block. No sorting by type, no notes inside it, they import it into another tool. Query fresh every time, they log purchases between asks.

## When a flow breaks

Sites change. When a step fails (planner finds nothing for a card the site clearly has, an endpoint 404s, a selector moved, the mass entry URL stops working):
1. Find the new way in the browser or with curl.
2. Fix `plan.py` or this file so the next run works without rediscovery.
3. Add a dated line to the log below saying what changed.
Tell the user in one line that the skill was updated.

## Change log

- 2026-10-16: A local line sent to TCGPlayer as cheaper (Ancient Copper Dragon, $140.75 local vs ~$125 market) came back from Mass Entry as a $143.56 foil, and Keep Current Printings kept it foil. After the optimizer, compare each card moved off a local store against its local price and move it back if TCGPlayer lost. Selecting the Direct cart by clicking its button with the computer tool worked. The optimizer's JS Optimize click did run, results just need a screenshot to read.
- 2026-10-16: StorePass reported stock -1 for some variants, plan.py picked them at qty -1 and bought the card twice elsewhere. Stock is now clamped at 0. Oversized box toppers (an 8ED Curiosity) are now skipped like art cards. On the optimizer, `document.getElementById('conditions-toggle').click()` did stick when the ref click did not.
- 2026-10-16: Direct swap solved by the built-in Cart Optimizer, it offers a TCGplayer Direct cart. Replaced the manual per-card swap steps.
- 2026-10-16: Added prep.py (resolve, drop digital-only, free-in-bulk, already-bought) and pull.py (bulk pull deck list). Added the TCGPlayer cart check script. Terrors of the Track, an Alchemy card, made Mass Entry reject the whole list.
- 2026-10-12: When the user says check a store first, run plan.py with `CARD_STORES=host1,host2` in the order wanted.
- 2026-10-12: Mass Entry added a $28.39 NM foil Necropede even though non-foil copies started at $0.15. Turning off the Foil checkbox from JS does not stick because React ignores it. After every Mass Entry, read each added line's price and remove anything far above market. In a hidden tab, clicking Remove with the computer tool does nothing. Clicking it from JS works: find the `li` that starts with the card name, then click its Remove button.

- 2026-10-11: Search API `lowestPrice` covers every condition, so it understates the price. Gate to Phyrexia showed $27.98 there, but Mass Entry added it at $59.99 LP against $53.50 LP locally. Compare the price the cart actually shows. Mass Entry also ignores shipping: it put three $0.01 cards on sellers charging $19.99 shipping each. Flag any seller with shipping over $5.

- 2026-10-10: Reports now include a Shopify cart permalink per local store.
- 2026-10-10: Foil fallback now price-checked against Scryfall. It had picked a $23.65 foil Zulaport and a $27 foil Cordial Vampire when TCGplayer Direct had both under $4.
- 2026-10-10: Added step 0, the ownership check. Never edit carts left over from an earlier run, the user may have checked them out already.
- 2026-10-09: the user's rules: cheapest printing always, and on TCGPlayer always prefer TCGplayer Direct. Mass Entry put Eternal Thirst ($0.05) on a separate seller with $4.99 shipping, which is why. Direct swap steps written but not yet run, TCGPlayer's cart was erroring on their side.
- 2026-10-09: First real run, 100 cards. Locals took 81 at about $406. Added $50 sanity cap and the no-navigate-in-script note.
- 2026-10-09: Created. Local stores Shopify/BinderPOS, StorePass stores searched through its API because its `/search` page is client-rendered. Stock probed via `/cart/add.js` with qty 99 in a throwaway session. Requests are sequential with backoff, the stores 429/503 on parallel bursts.
- 2026-10-09: Foil fallback is global. Non-foil pass runs through all three locals before any foil is picked, so a $9 foil at store 1 never beats a $0.50 non-foil at store 2.
- 2026-10-09: TCGPlayer Mass Entry URL verified live: `massentry?productline=Magic&c=1 Name||1 Name` prefills the list, two Add to Cart clicks (page then dialog) fill the cart.
- 2026-10-22: One store's `/products/<handle>.js` 429'd through the full 9-try backoff twice on card 2. Slowed plan.py to 1s between requests and 12 retries backing off up to 300s.
- 2026-10-22: Rewrote plan.py for aggregate lookups only. Shopify stores get ONE `title:"A" OR title:"B"` search paged to the end, each search page carries variant ids, conditions, prices (`variants='{...}'`) and `data-available` per variant, so no product pages are fetched. StorePass replies carry price and stock, so StorePass hosts get no requests. Scryfall floors via one /cards/collection call. The old per-printing fetches got a store to 429 every product URL from our IP. StorePass name match is now exact title, a handle prefix let Snapdax through for Snap. StorePass stock can be stale (Spark Double sold out at cart add).
