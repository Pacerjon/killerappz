#!/usr/bin/env python3
"""Checks app/content.json before it is published. The Listworthy app ignores
the whole file if it doesn't decode, so a bad push would silently drop every
seasonal pack. Exit code 1 on any error.

usage: python3 app/validate_content.py [path]   (default: app/content.json)
Also prints which packs are live today and which start in the next 60 days.
"""
import json, sys, datetime

CATEGORIES = {"movies", "tv", "games", "books", "music", "comics"}
MEDIA = {"Movies", "TV Shows", "Music", "Books", "Games", "Comics", "Places", "Products", "Miscellaneous", "Links"}

def md(s):
    m, d = s.split("-")
    m, d = int(m), int(d)
    assert 1 <= m <= 12 and 1 <= d <= 31
    datetime.date(2028, m, d)  # leap year, so 02-29 is allowed
    return m * 100 + d

def active(start, end, day):
    a, b, t = md(start), md(end), day.month * 100 + day.day
    return a <= t <= b if a <= b else (t >= a or t <= b)

def main(path):
    errors, warnings = [], []
    try:
        with open(path, encoding="utf-8") as f:
            c = json.load(f)
    except Exception as e:
        print(f"ERROR: not valid JSON: {e}")
        return 1

    if c.get("version") != 1:
        errors.append("version must be 1")
    packs = c.get("packs", [])
    ids = set()
    for p in packs:
        pid = p.get("id", "?")
        for key in ("id", "title", "emoji", "category", "start", "end", "items"):
            if key not in p:
                errors.append(f"{pid}: missing {key}")
        if pid in ids:
            errors.append(f"duplicate pack id {pid}")
        ids.add(pid)
        if p.get("category") not in CATEGORIES:
            errors.append(f"{pid}: category must be one of {sorted(CATEGORIES)}")
        if p.get("itemType") not in (None, "song"):
            errors.append(f"{pid}: itemType must be 'song' or absent")
        if p.get("itemType") == "song" and p.get("category") != "music":
            errors.append(f"{pid}: song packs must use category music")
        for key in ("start", "end"):
            try:
                md(p.get(key, ""))
            except Exception:
                errors.append(f"{pid}: {key} must be MM-dd, got {p.get(key)!r}")
        items = p.get("items", [])
        if len(items) < 12:
            errors.append(f"{pid}: needs at least 12 items, has {len(items)}")
        elif len(items) < 20:
            warnings.append(f"{pid}: only {len(items)} items (a round is 20 picks)")
        seen = set()
        for it in items:
            t = (it.get("title") or "").strip()
            if not t:
                errors.append(f"{pid}: item with no title")
            if t.lower() in seen:
                errors.append(f"{pid}: duplicate item {t!r}")
            seen.add(t.lower())
            y = it.get("year")
            if y is not None and not (isinstance(y, str) and len(y) == 4 and y.isdigit()):
                errors.append(f"{pid}: {t!r} year must be a 4-digit string")
            if p.get("category") in ("books", "music") and not it.get("byline"):
                warnings.append(f"{pid}: {t!r} has no byline (author/artist); cover lookup is less accurate")

    t = c.get("templates") or {}
    for tpl in t.get("add") or []:
        name = tpl.get("title", "?")
        if tpl.get("category") not in MEDIA:
            errors.append(f"template {name}: category must be one of {sorted(MEDIA)}")
        if not tpl.get("items"):
            errors.append(f"template {name}: needs items")
        if ("start" in tpl) != ("end" in tpl):
            errors.append(f"template {name}: give both start and end, or neither")
    # 4.5+: gift list / recipe templates (empty lists that fill from the share sheet).
    # Kept under "styled" so 4.1 and older never see them.
    for tpl in t.get("styled") or []:
        name = tpl.get("title", "?")
        if tpl.get("style") not in ("gifts", "recipes"):
            errors.append(f"styled template {name}: style must be gifts or recipes")
        want = "Products" if tpl.get("style") == "gifts" else "Links"
        if tpl.get("category") != want:
            errors.append(f"styled template {name}: category must be {want} for {tpl.get('style')}")
        if "items" not in tpl:
            errors.append(f"styled template {name}: needs an items array (can be empty)")
        if ("start" in tpl) != ("end" in tpl):
            errors.append(f"styled template {name}: give both start and end, or neither")
        for key in ("start", "end"):
            if key in tpl:
                try:
                    md(tpl[key])
                except Exception:
                    errors.append(f"styled template {name}: {key} must be MM-dd")
    cur = c.get("curated") or {}
    for key in ("books", "comics", "albums"):
        lst = cur.get(key)
        if lst is not None and len(lst) < 20:
            errors.append(f"curated.{key}: needs at least 20 items or the app ignores it")

    today = datetime.date.today()
    live = [p["id"] for p in packs if "start" in p and active(p["start"], p["end"], today)]
    soon = set()
    for n in range(1, 61):
        d = today + datetime.timedelta(days=n)
        for p in packs:
            try:
                if p["id"] not in live and active(p["start"], p["end"], d):
                    soon.add(f'{p["id"]} (from {p["start"]})')
            except Exception:
                pass

    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    print(f"{len(packs)} packs, {sum(len(p.get('items', [])) for p in packs)} items")
    print("live today:", ", ".join(live) or "none")
    print("starting in the next 60 days:", ", ".join(sorted(soon)) or "none")
    print("OK" if not errors else f"FAILED with {len(errors)} errors")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "app/content.json"))
