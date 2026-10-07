"""Collect members' latest posts from their Substack (or any RSS) feeds.

Reads `substack:` or `feed:` from each file in _members/ and writes
_data/feed.json, which the home, blog and member pages read from.
A feed that fails to load is skipped so one broken link can't stop the site building.
"""

import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_PER_MEMBER = 10
RELAY = "https://api.rss2json.com/v1/api.json?rss_url="


def front_matter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---", text, re.S)
    fields = {"hide": []}
    in_hide = False
    for line in (match.group(1) if match else "").splitlines():
        m = re.match(r"^(substack|feed):\s*(\S+)", line)
        if m:
            fields[m.group(1)] = m.group(2).strip("\"'")
        item = re.match(r"^\s+-\s*(.+)", line)
        if in_hide and item:
            fields["hide"].append(item.group(1).strip().strip("\"'").lower())
        else:
            in_hide = line.startswith("hide:")
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
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36 (+https://firstfewbooks.com)",
        "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8",
    })
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()


def read_feed(url):
    """Return the feed's items as (title, link, date, excerpt, image) tuples."""
    items = []
    for item in ET.fromstring(fetch(url)).iter("item"):
        pub_date = item.findtext("pubDate")
        enclosure = item.find("enclosure")
        image = enclosure.get("url") if enclosure is not None and "image" in (enclosure.get("type") or "") else None
        items.append((
            item.findtext("title"),
            (item.findtext("link") or "").strip(),
            parsedate_to_datetime(pub_date) if pub_date else None,
            item.findtext("description"),
            image,
        ))
    return items


def read_feed_via_relay(url):
    """Substack blocks requests from GitHub's servers, so fetch through rss2json instead."""
    data = json.loads(fetch(RELAY + urllib.parse.quote(url, safe="")))
    if data.get("status") != "ok":
        raise RuntimeError(data.get("message", "relay error"))
    return [(
        item.get("title"),
        (item.get("link") or "").strip(),
        datetime.strptime(item["pubDate"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc) if item.get("pubDate") else None,
        item.get("description"),
        (item.get("enclosure") or {}).get("link") or item.get("thumbnail") or None,
    ) for item in data.get("items", [])]


def to_posts(items, author, hide=()):
    posts = []
    for title, link, date, excerpt, image in items:
        title = plain_text(title)
        if not link or not date or title.lower() in hide or link.rstrip("/").lower() in hide:
            continue
        posts.append({
            "title": title,
            "url": link,
            "date": date.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "excerpt": plain_text(excerpt)[:300],
            "image": image,
            "author": author,
        })
    return posts[:POSTS_PER_MEMBER]


def main():
    posts = []
    for path in sorted((ROOT / "_members").glob("*.md")):
        fields = front_matter(path)
        url = feed_url(fields)
        if not url:
            continue
        try:
            items = read_feed(url)
        except Exception as error:
            try:
                items = read_feed_via_relay(url)
                print(f"{path.stem}: direct fetch failed ({error}), used relay")
            except Exception as relay_error:
                # "::warning::" makes the message show up on the GitHub Actions run.
                print(f"::warning::{path.stem}: feed skipped ({error}; relay: {relay_error})")
                continue
        posts += to_posts(items, path.stem, fields["hide"])
        print(f"{path.stem}: ok")

    posts.sort(key=lambda post: post["date"], reverse=True)
    out = ROOT / "_data" / "feed.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(posts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(posts)} posts written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
