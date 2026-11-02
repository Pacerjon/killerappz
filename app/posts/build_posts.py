#!/usr/bin/env python3
"""Listworthy app posts: fun posts about the app's features for social media.

posts.json holds the posts (newest last). This script validates them and
rebuilds app/posts.xml, the RSS feed a Make scenario reads to post photos to
the Listworthy App Facebook page.

Add a post:   python3 app/posts/build_posts.py --add '<json object>'
Rebuild only: python3 app/posts/build_posts.py

Post keys: id (kebab-case, unique), date (YYYY-MM-DD), title (short, for the
feed), caption (the full post text, no URL; the script adds the App Store
link), card (an image slug from app/posts/cards/).
This script never touches deals/.
"""
import json, os, sys, html, re
from datetime import datetime, timezone
from email.utils import format_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
POSTS = os.path.join(HERE, "posts.json")
CONFIG = os.path.join(HERE, "config.json")
OUT = os.path.join(os.path.dirname(HERE), "posts.xml")
SITE = "https://killerappz.dev"
KEEP = 30
CARDS = sorted(f[:-4] for f in os.listdir(os.path.join(HERE, "cards")) if f.endswith(".jpg"))

def app_link(campaign):
    cfg = json.load(open(CONFIG))
    q = ["ppid=" + cfg["ppid"]]
    if cfg.get("provider_token"):
        q += ["pt=" + cfg["provider_token"], "ct=" + campaign]
    return "https://apps.apple.com/us/app/listworthy/id6752911163?" + "&".join(q)

def check(p, ids):
    errs = []
    for k in ("id", "date", "title", "caption", "card"):
        if not str(p.get(k, "")).strip():
            errs.append(f"missing {k}")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", p.get("id", "")):
        errs.append("id must be kebab-case")
    if p.get("id") in ids:
        errs.append(f"duplicate id {p.get('id')}")
    try:
        datetime.strptime(p.get("date", ""), "%Y-%m-%d")
    except ValueError:
        errs.append("date must be YYYY-MM-DD")
    if p.get("card") not in CARDS:
        errs.append(f"card must be one of {CARDS}")
    c = p.get("caption", "")
    if "http" in c or "www." in c:
        errs.append("caption must not contain a URL (the script adds the link)")
    if "—" in c or "—" in p.get("title", ""):
        errs.append("no em dashes")
    if len(c) > 700:
        errs.append(f"caption too long ({len(c)} chars, max 700)")
    return errs

def build(posts):
    link = app_link("fb-app")
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">',
           '<channel>',
           '<title>Listworthy | App posts</title>',
           f'<link>{SITE}/listworthy.html</link>',
           '<description>Fun posts about Listworthy, the free ranking and list app for iPhone.</description>',
           '<language>en-us</language>']
    for p in reversed(posts[-KEEP:]):
        img = f"{SITE}/app/posts/cards/{p['card']}.jpg"
        when = datetime.strptime(p["date"], "%Y-%m-%d").replace(hour=12, tzinfo=timezone.utc)
        text = p["caption"].rstrip() + "\n\nFree on the App Store: " + link
        out += ['<item>',
                f'<title>{html.escape(p["title"], quote=False)}</title>',
                f'<link>{html.escape(link)}</link>',
                f'<guid isPermaLink="false">lw-post-{html.escape(p["id"])}</guid>',
                f'<pubDate>{format_datetime(when)}</pubDate>',
                f'<description>{html.escape(text, quote=False)}</description>',
                f'<enclosure url="{img}" type="image/jpeg" length="0"/>',
                f'<media:content url="{img}" medium="image" type="image/jpeg"/>',
                '</item>']
    out += ['</channel>', '</rss>', '']
    open(OUT, "w", encoding="utf-8").write("\n".join(out))

def main():
    posts = json.load(open(POSTS, encoding="utf-8"))
    if len(sys.argv) > 2 and sys.argv[1] == "--add":
        p = json.loads(sys.argv[2])
        errs = check(p, {x["id"] for x in posts})
        if errs:
            print("ERROR: " + "; ".join(errs)); sys.exit(1)
        posts.append(p)
        json.dump(posts, open(POSTS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    seen = set()
    for p in posts:
        errs = check(p, seen); seen.add(p["id"])
        if errs:
            print(f"ERROR in {p.get('id')}: " + "; ".join(errs)); sys.exit(1)
    build(posts)
    recent = [p["card"] for p in posts[-4:]]
    print(f"OK {len(posts)} posts; recent cards: {recent}; cards: {CARDS}")

if __name__ == "__main__":
    main()
