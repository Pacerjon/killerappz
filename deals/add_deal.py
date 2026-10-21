#!/usr/bin/env python3
"""Add a deal to the Listworthy Pinterest RSS feeds.

Usage: python3 deals/add_deal.py '<json>'
JSON keys: board (kitchen|home|travel|tech|gifts), title, description,
link, image, asin. Optional: store ("ebay"), social, social_link, and for the
app feed: price, list_price, pct_off, category, coupon, condition, price_checked.
Rebuilds deals/<board>.xml, the deal pages, and deals/feed.json (Listworthy app).
"""
import json, sys, os, html
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from email.utils import format_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "deals.json")
SITE = "https://killerappz.dev"
BOARDS = {
    "kitchen": "Kitchen Deals",
    "home": "Home Deals",
    "travel": "Travel Deals",
    "tech": "Tech Deals",
    "gifts": "Holiday Gift Deals",
}
KEEP = 50
FEED = os.path.join(HERE, "feed.json")  # read by the Listworthy iOS app
FEED_DAYS = 14
APP_TAG = "listworthy-app-20"
APP_EBAY_CUSTOMID = "app"

def esc(s):
    return html.escape(str(s), quote=True)

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} | Listworthy Deals</title>
  <meta name="description" content="{desc}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:image" content="{image}">
  <meta property="og:type" content="product">
  <link rel="icon" type="image/png" href="../assets/appicon.png">
  <link rel="stylesheet" href="../styles.css">
  <style>
    .deal{{max-width:720px;margin:0 auto;padding:32px 16px;text-align:center}}
    .deal img.product{{max-width:100%;max-height:480px;border-radius:12px;background:#fff}}
    .deal h1{{font-size:1.6rem;margin:20px 0 10px}}
    .deal .disc{{font-size:.85rem;opacity:.7;margin-top:18px}}
    .deal .more{{margin-top:28px}}
  </style>
</head>
<body>
  <header class="site-header"><div class="container nav">
    <a class="brand" href="../index.html"><span class="mark">K</span> KillerAppz</a>
    <button class="nav-toggle" aria-label="Menu" onclick="document.getElementById('nav').classList.toggle('open')">☰</button><nav class="nav-links" id="nav"><a href="../index.html">Home</a><a href="../listworthy.html">Listworthy</a><a href="../affiliate.html">Recommends</a><a href="index.html" class="active">Deals</a><a href="../support.html">Support</a><a href="../privacy.html">Privacy</a></nav>
  </div></header>
  <main class="deal">
    <img class="product" src="{image}" alt="{title}">
    <h1>{title}</h1>
    <p>{body}</p>
    <p><a class="btn btn-primary" id="deal-btn" href="{link}" rel="sponsored nofollow noopener">View deal on {store} &rarr;</a></p>
    <p class="disc">Price as of {asof}. Prices and availability can change; check {store} for the current price. {disclosure}</p>
    <p class="more"><a href="index.html">See more daily deals</a></p>
  </main>
  <script>
    // Per-channel tracking: ?src=fb|pin|social|rd swaps the Amazon tag (or eBay customid).
    (function(){{
      try {{
        var tags = {{fb: "listworthy-fb-20", pin: "listworthy-pin-20", social: "listworthy-social-20", rd: "listworthy-rd-20", app: "listworthy-app-20"}};
        var src = new URLSearchParams(location.search).get("src");
        if (!src || !tags[src]) return;
        var a = document.getElementById("deal-btn");
        var u = new URL(a.href);
        if (u.hostname.indexOf("ebay.") !== -1) u.searchParams.set("customid", src);
        else if (u.hostname.indexOf("amazon.") !== -1) u.searchParams.set("tag", tags[src]);
        a.href = u.toString();
      }} catch (e) {{}}
    }})();
  </script>
</body>
</html>
"""

def asof(d):
    dt = datetime.fromisoformat(d["date"]).astimezone()
    return dt.strftime("%b %-d, %Y %-I:%M %p ") + (dt.tzname() or "")

def store_name(d):
    return "eBay" if d.get("store") == "ebay" else "Amazon"

def disclosure(d):
    if d.get("store") == "ebay":
        return "As an eBay Partner Network affiliate, I may earn a commission from qualifying purchases."
    return "As an Amazon Associate I earn from qualifying purchases."

def page_url(d):
    return f"{SITE}/deals/{d['asin']}.html"

def write_page(d):
    body = d["description"].split(" #")[0]
    with open(os.path.join(HERE, f"{d['asin']}.html"), "w", encoding="utf-8") as f:
        f.write(PAGE.format(title=esc(d["title"]), desc=esc(body), body=esc(body),
                            image=esc(d["image"]), link=esc(d["link"]), asof=esc(asof(d)),
                            store=store_name(d), disclosure=disclosure(d)))

def write_index(deals):
    rows = []
    seen = set()
    for d in reversed(deals):
        if d["asin"] in seen:
            continue
        seen.add(d["asin"])
        rows.append(f'<a class="card" href="{esc(d["asin"])}.html" style="display:block;text-align:center">'
                    f'<img src="{esc(d["image"])}" alt="" style="max-width:100%;height:180px;object-fit:contain;background:#fff;border-radius:8px">'
                    f'<h3 style="font-size:1rem;margin-top:10px">{esc(d["title"])}</h3>'
                    f'<p class="deal-asof">Price as of {esc(asof(d))}</p></a>')
        if len(rows) >= 60:
            break
    html_out = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Amazon Deals | Listworthy</title>
<meta name="description" content="Hand-picked Amazon deals, updated daily.">
<link rel="icon" type="image/png" href="../assets/appicon.png"><link rel="stylesheet" href="../styles.css"></head>
<body><header class="site-header"><div class="container nav"><a class="brand" href="../index.html"><span class="mark">K</span> KillerAppz</a>
<button class="nav-toggle" aria-label="Menu" onclick="document.getElementById('nav').classList.toggle('open')">☰</button><nav class="nav-links" id="nav"><a href="../index.html">Home</a><a href="../listworthy.html">Listworthy</a><a href="../affiliate.html">Recommends</a><a href="index.html" class="active">Deals</a><a href="../support.html">Support</a><a href="../privacy.html">Privacy</a></nav></div></header>
<section><div class="container"><div class="center" style="margin-bottom:30px"><span class="eyebrow">Updated daily</span><h2>Listworthy Daily Deals</h2>
<p>Hand-picked Amazon and eBay deals on brands worth buying. As an Amazon Associate and eBay Partner Network affiliate, I earn from qualifying purchases.</p></div>
<div class="grid grid-3">{''.join(rows)}</div></div></section></body></html>
"""
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_out)

def write_recommends(deals):
    path = os.path.join(HERE, "..", "affiliate.html")
    if not os.path.exists(path):
        return
    page = open(path, encoding="utf-8").read()
    a, b = "<!-- DEALS:START -->", "<!-- DEALS:END -->"
    if a not in page or b not in page:
        return
    latest, seen = [], set()
    for d in reversed(deals):
        if d["asin"] in seen:
            continue
        seen.add(d["asin"])
        latest.append(d)
        if len(latest) == 3:
            break
    cards = "".join(
        f'''
        <div class="aff">
          <div class="thumb photo"><img src="{esc(d["image"])}" alt="" loading="lazy"></div>
          <h3>{esc(d["title"])}</h3>
          <p class="deal-asof" style="flex:1;">Price as of {esc(asof(d))}</p>
          <a class="btn btn-primary" href="deals/{esc(d["asin"])}.html">See the deal</a>
        </div>''' for d in latest)
    block = (a + '''
      <h2 style="margin-bottom:8px;">Today's deals</h2>
      <p style="color:var(--ink-soft);margin-bottom:22px;">Hand-picked Amazon deals, updated every morning. <a href="deals/">See all deals &rarr;</a></p>
      <div class="aff-grid" style="margin-bottom:44px;">''' + cards + '''
      </div>
      ''' + b)
    page = page[:page.index(a)] + block + page[page.index(b) + len(b):]
    open(path, "w", encoding="utf-8").write(page)

def build(board, deals):
    items = (deals if board == "all" else [d for d in deals if d["board"] == board])[-KEEP:]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">',
           '<channel>',
           f'<title>Listworthy | {esc(BOARDS.get(board, "Daily Deals"))}</title>',
           f'<link>{SITE}/</link>',
           f'<description>Hand-picked Amazon and eBay deals: {esc(BOARDS.get(board, "Daily Deals"))}. I may earn a commission from qualifying purchases.</description>',
           '<language>en-us</language>']
    # all.xml is read by the Make -> Facebook scenario; board feeds are read by Pinterest.
    src = "fb" if board == "all" else "pin"
    for d in reversed(items):
        out += ['<item>',
                f'<title>{esc(d["title"])}</title>',
                f'<link>{esc(page_url(d))}?src={src}</link>',
                f'<guid isPermaLink="false">{esc(d["asin"])}-{esc(d["date"][:10])}</guid>',
                f'<pubDate>{esc(d["pubDate"])}</pubDate>',
                f'<description>{esc(d["description"])}</description>',
                f'<enclosure url="{esc(d["image"])}" type="image/jpeg" length="0"/>',
                f'<media:content url="{esc(d["image"])}" medium="image" type="image/jpeg"/>',
                '</item>']
    out += ['</channel>', '</rss>', '']
    with open(os.path.join(HERE, f"{board}.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))

def num(v):
    """Coerce '$1,299.99', '41%', 41 or None to a float or None."""
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace("$", "").replace(",", "").replace("%", "").strip())
    except ValueError:
        return None

def app_link(d):
    """Affiliate link the app opens directly, tagged for the app channel."""
    if d.get("store") == "ebay":
        u = urlparse(d["link"])
        q = dict(parse_qsl(u.query))
        q["customid"] = APP_EBAY_CUSTOMID
        return urlunparse(u._replace(query=urlencode(q)))
    return f"https://www.amazon.com/dp/{d['asin']}?tag={APP_TAG}"

def write_feed(deals):
    """Stable, versioned JSON contract for the Listworthy app (newest first)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=FEED_DAYS)
    items, seen = [], set()
    for d in reversed(deals):
        if d["asin"] in seen or datetime.fromisoformat(d["date"]) < cutoff:
            continue
        seen.add(d["asin"])
        store = d.get("store", "amazon")
        items.append({
            "id": f'{d["asin"]}-{d["date"][:10]}',
            "store": store,
            "asin": d["asin"] if store == "amazon" else None,
            "ebay_item_id": d["asin"][5:] if store == "ebay" else None,
            "board": d["board"],
            "category": d.get("category"),
            "title": d["title"],
            "summary": d["description"].split(" #")[0],
            "price": num(d.get("price")),
            "list_price": num(d.get("list_price")),
            "pct_off": num(d.get("pct_off")),
            "coupon": bool(d.get("coupon", False)),
            "condition": d.get("condition"),
            "image": d["image"],
            "url": app_link(d),
            "page": page_url(d) + "?src=app",
            "price_checked": d.get("price_checked") or d["date"],
            "posted": d["date"],
        })
    out = {"version": 1, "generated": datetime.now(timezone.utc).isoformat(),
           "boards": BOARDS, "deals": items}
    with open(FEED, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)

def main():
    deals = json.load(open(DATA)) if os.path.exists(DATA) else []
    if len(sys.argv) > 1:
        d = json.loads(sys.argv[1])
        assert d["board"] in BOARDS, f"board must be one of {list(BOARDS)}"
        for k in ("title", "description", "link", "image", "asin"):  # asin = Amazon ASIN or "ebay-<itemId>"; optional "store": "ebay"
            assert d.get(k), f"missing {k}"
        for k in ("price", "list_price", "pct_off"):  # optional structured fields for the app feed
            if k in d:
                d[k] = num(d[k])
        now = datetime.now(timezone.utc)
        d["date"] = now.isoformat()
        d["pubDate"] = format_datetime(now)
        if not any(x["asin"] == d["asin"] and x["date"][:10] == d["date"][:10] for x in deals):
            deals.append(d)
        json.dump(deals, open(DATA, "w"), indent=1)
    for d in deals:
        write_page(d)
    write_index(deals)
    write_recommends(deals)
    for b in BOARDS:
        build(b, deals)
    build("all", deals)
    write_feed(deals)

if __name__ == "__main__":
    main()
