#!/usr/bin/env python3
"""Post new deals to Bluesky. Run by .github/workflows/bluesky.yml.

Posts every deal that is in deals/deals.json now but wasn't in the previous
commit and that has a "social" field (the ready-to-post text). Adds a link
preview card (title, description, product photo) for "social_link".
Env: BSKY_HANDLE, BSKY_APP_PASSWORD, BEFORE_SHA (previous commit), DRY_RUN.
"""
import json, os, re, subprocess, sys, urllib.request, urllib.error
from datetime import datetime, timezone

PDS = "https://bsky.social/xrpc/"
HERE = os.path.dirname(os.path.abspath(__file__))

def xrpc(method, body=None, token=None, raw=None, ctype="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(PDS + method, data=data, method="POST" if data is not None else "GET")
    if data is not None:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        sys.exit(f"Bluesky {method} failed: {e.code} {e.read().decode()[:300]}")

def facets(text):
    out = []
    b = text.encode("utf-8")
    def span(m):
        start = len(text[:m.start()].encode("utf-8"))
        return {"byteStart": start, "byteEnd": start + len(m.group(0).encode("utf-8"))}
    for m in re.finditer(r"https?://[^\s]+", text):
        out.append({"index": span(m), "features": [{"$type": "app.bsky.richtext.facet#link", "uri": m.group(0)}]})
    for m in re.finditer(r"(?<![\w/])#([A-Za-z][A-Za-z0-9_]*)", text):
        out.append({"index": span(m), "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": m.group(1)}]})
    return out

def small_image(url):
    url = re.sub(r"\._AC_SL\d+_\.", "._AC_SL500_.", url)
    url = re.sub(r"s-l\d+\.", "s-l500.", url)
    return url

def fetch_thumb(url, token):
    try:
        req = urllib.request.Request(small_image(url), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data, ctype = r.read(), r.headers.get("Content-Type", "image/jpeg")
        if len(data) > 950_000:
            print("thumbnail too large, skipping"); return None
        return xrpc("com.atproto.repo.uploadBlob", raw=data, token=token, ctype=ctype)["blob"]
    except Exception as e:
        print("thumbnail skipped:", e); return None

def load(sha):
    if sha and not set(sha) <= {"0"}:
        try:
            return json.loads(subprocess.check_output(["git", "show", f"{sha}:deals/deals.json"]))
        except subprocess.CalledProcessError:
            pass
    return []

def main():
    now = json.load(open(os.path.join(HERE, "deals.json")))
    before = load(os.environ.get("BEFORE_SHA", ""))
    old = {(d["asin"], d["date"]) for d in before}
    new = [d for d in now if (d["asin"], d["date"]) not in old and d.get("social")]
    dry = os.environ.get("DRY_RUN", "false").lower() == "true"
    if dry and not new and now:
        new = [dict(now[-1], social=now[-1].get("social") or ("TEST " + now[-1]["title"] + " #AmazonDeals"))]
    if not new:
        print("No new deals with social text; nothing to post."); return
    sess = xrpc("com.atproto.server.createSession",
                {"identifier": os.environ["BSKY_HANDLE"], "password": os.environ["BSKY_APP_PASSWORD"]})
    token, did = sess["accessJwt"], sess["did"]
    print("Logged in as", sess.get("handle"))
    for d in new:
        text = d["social"].strip()
        if len(text) > 300:
            sys.exit(f"Post too long ({len(text)} chars): {d['asin']}")
        record = {"$type": "app.bsky.feed.post", "text": text, "facets": facets(text),
                  "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "langs": ["en"]}
        link = d.get("social_link")
        if link:
            ext = {"uri": link, "title": d["title"][:300], "description": d["description"].split(" #")[0][:300]}
            thumb = fetch_thumb(d["image"], token)
            if thumb:
                ext["thumb"] = thumb
            record["embed"] = {"$type": "app.bsky.embed.external", "external": ext}
        if dry:
            print("DRY RUN, would post:\n" + json.dumps(record, indent=1)[:1500]); continue
        res = xrpc("com.atproto.repo.createRecord", {"repo": did, "collection": "app.bsky.feed.post", "record": record}, token=token)
        print("Posted", d["asin"], res.get("uri"))

if __name__ == "__main__":
    main()
