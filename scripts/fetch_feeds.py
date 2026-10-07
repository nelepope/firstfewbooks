"""Collect members' latest posts from their Substack (or any RSS) feeds.

Reads `substack:` or `feed:` from each file in _members/ and writes
_data/feed.json, which the home, blog and member pages read from.
A feed that fails to load is skipped so one broken link can't stop the site building.
"""

import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_PER_MEMBER = 10


def front_matter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---", text, re.S)
    fields = {}
    for line in (match.group(1) if match else "").splitlines():
        m = re.match(r"^(substack|feed):\s*(\S+)", line)
        if m:
            fields[m.group(1)] = m.group(2).strip("\"'")
    return fields


def feed_url(fields):
    if "feed" in fields:
        return fields["feed"]
    if "substack" in fields:
        # Accept "name", "@name", "name.substack.com" or a link to one post: keep just the site's address.
        address = fields["substack"].lstrip("@")
        if "." not in address:
            address += ".substack.com"
        if "://" not in address:
            address = "https://" + address
        scheme, rest = address.split("://", 1)
        return f"{scheme}://{rest.split('/')[0]}/feed"
    return None


def plain_text(value):
    text = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "firstfewbooks.com feed reader"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def parse(xml, author):
    posts = []
    for item in ET.fromstring(xml).iter("item"):
        link = (item.findtext("link") or "").strip()
        pub_date = item.findtext("pubDate")
        if not link or not pub_date:
            continue
        enclosure = item.find("enclosure")
        image = enclosure.get("url") if enclosure is not None and "image" in (enclosure.get("type") or "") else None
        posts.append({
            "title": plain_text(item.findtext("title")),
            "url": link,
            "date": parsedate_to_datetime(pub_date).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "excerpt": plain_text(item.findtext("description"))[:300],
            "image": image,
            "author": author,
        })
    return posts[:POSTS_PER_MEMBER]


def main():
    posts = []
    for path in sorted((ROOT / "_members").glob("*.md")):
        url = feed_url(front_matter(path))
        if not url:
            continue
        try:
            posts += parse(fetch(url), path.stem)
            print(f"{path.stem}: ok")
        except Exception as error:
            print(f"{path.stem}: skipped ({error})", file=sys.stderr)

    posts.sort(key=lambda post: post["date"], reverse=True)
    out = ROOT / "_data" / "feed.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(posts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(posts)} posts written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
