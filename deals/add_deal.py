#!/usr/bin/env python3
"""Add a deal to the Listworthy Pinterest RSS feeds.

Usage: python3 deals/add_deal.py '<json>'
JSON keys: board (kitchen|home|travel|tech|gifts), title, description,
link, image, asin. Rebuilds deals/<board>.xml from deals/deals.json.
"""
import json, sys, os, html
from datetime import datetime, timezone
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
    <nav class="nav-links"><a href="index.html">Deals</a><a href="../listworthy.html">Listworthy</a></nav>
  </div></header>
  <main class="deal">
    <img class="product" src="{image}" alt="{title}">
    <h1>{title}</h1>
    <p>{body}</p>
    <p><a class="btn btn-primary" href="{link}" rel="sponsored nofollow noopener">View deal on Amazon &rarr;</a></p>
    <p class="disc">Prices and availability can change. As an Amazon Associate I earn from qualifying purchases.</p>
    <p class="more"><a href="index.html">See more daily deals</a></p>
  </main>
</body>
</html>
"""

def page_url(d):
    return f"{SITE}/deals/{d['asin']}.html"

def write_page(d):
    body = d["description"].split(" #")[0]
    with open(os.path.join(HERE, f"{d['asin']}.html"), "w", encoding="utf-8") as f:
        f.write(PAGE.format(title=esc(d["title"]), desc=esc(body), body=esc(body),
                            image=esc(d["image"]), link=esc(d["link"])))

def write_index(deals):
    rows = []
    seen = set()
    for d in reversed(deals):
        if d["asin"] in seen:
            continue
        seen.add(d["asin"])
        rows.append(f'<a class="card" href="{esc(d["asin"])}.html" style="display:block;text-align:center">'
                    f'<img src="{esc(d["image"])}" alt="" style="max-width:100%;height:180px;object-fit:contain;background:#fff;border-radius:8px">'
                    f'<h3 style="font-size:1rem;margin-top:10px">{esc(d["title"])}</h3></a>')
        if len(rows) >= 60:
            break
    html_out = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Amazon Deals | Listworthy</title>
<meta name="description" content="Hand-picked Amazon deals, updated daily.">
<link rel="icon" type="image/png" href="../assets/appicon.png"><link rel="stylesheet" href="../styles.css"></head>
<body><header class="site-header"><div class="container nav"><a class="brand" href="../index.html"><span class="mark">K</span> KillerAppz</a>
<nav class="nav-links"><a href="index.html" class="active">Deals</a><a href="../listworthy.html">Listworthy</a></nav></div></header>
<section><div class="container"><div class="center" style="margin-bottom:30px"><span class="eyebrow">Updated daily</span><h2>Listworthy Daily Deals</h2>
<p>Hand-picked Amazon deals on brands worth buying. As an Amazon Associate I earn from qualifying purchases.</p></div>
<div class="grid grid-3">{''.join(rows)}</div></div></section></body></html>
"""
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_out)

def build(board, deals):
    items = [d for d in deals if d["board"] == board][-KEEP:]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">',
           '<channel>',
           f'<title>Listworthy | {esc(BOARDS[board])}</title>',
           f'<link>{SITE}/</link>',
           f'<description>Hand-picked Amazon deals: {esc(BOARDS[board])}. As an Amazon Associate I earn from qualifying purchases.</description>',
           '<language>en-us</language>']
    for d in reversed(items):
        out += ['<item>',
                f'<title>{esc(d["title"])}</title>',
                f'<link>{esc(page_url(d))}</link>',
                f'<guid isPermaLink="false">{esc(d["asin"])}-{esc(d["date"][:10])}</guid>',
                f'<pubDate>{esc(d["pubDate"])}</pubDate>',
                f'<description>{esc(d["description"])}</description>',
                f'<enclosure url="{esc(d["image"])}" type="image/jpeg" length="0"/>',
                f'<media:content url="{esc(d["image"])}" medium="image" type="image/jpeg"/>',
                '</item>']
    out += ['</channel>', '</rss>', '']
    with open(os.path.join(HERE, f"{board}.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))

def main():
    deals = json.load(open(DATA)) if os.path.exists(DATA) else []
    if len(sys.argv) > 1:
        d = json.loads(sys.argv[1])
        assert d["board"] in BOARDS, f"board must be one of {list(BOARDS)}"
        for k in ("title", "description", "link", "image", "asin"):
            assert d.get(k), f"missing {k}"
        now = datetime.now(timezone.utc)
        d["date"] = now.isoformat()
        d["pubDate"] = format_datetime(now)
        if not any(x["asin"] == d["asin"] and x["date"][:10] == d["date"][:10] for x in deals):
            deals.append(d)
        json.dump(deals, open(DATA, "w"), indent=1)
    for d in deals:
        write_page(d)
    write_index(deals)
    for b in BOARDS:
        build(b, deals)

if __name__ == "__main__":
    main()
