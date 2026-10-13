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
                f'<link>{esc(d["link"])}</link>',
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
    for b in BOARDS:
        build(b, deals)

if __name__ == "__main__":
    main()
