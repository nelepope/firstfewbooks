"""Collect members' latest posts from their Substack (or any RSS) feeds.

Reads `substack:` or `feed:` from each file in _members/ and writes
_data/feed.json, which the home, blog and member pages read from.
A feed that fails to load is skipped so one broken link can't stop the site building.
"""

import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_PER_MEMBER = 10
RELAY = "https://api.rss2json.com/v1/api.json?rss_url="
# A copy of the posts published with the site (see feed-cache.json at the site root).
PREVIOUS = "https://firstfewbooks.com/feed-cache.json"


def front_matter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(.*?)\n---", text, re.S)
    fields = {"hide": [], "mute": []}
    in_list = None
    for line in (match.group(1) if match else "").splitlines():
        m = re.match(r"^(substack|feed):\s*(\S+)", line)
        if m:
            fields[m.group(1)] = m.group(2).strip("\"'")
        item = re.match(r"^\s+-\s*(.+)", line)
        if in_list and item:
            fields[in_list].append(item.group(1).strip().strip("\"'").lower())
        else:
            in_list = next((k for k in ("hide", "mute") if line.startswith(k + ":")), None)
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


def to_posts(items, author, hide=(), mute=()):
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
            "muted": title.lower() in mute or link.rstrip("/").lower() in mute,
            "author": author,
        })
    return posts[:POSTS_PER_MEMBER]


def fetch_with_retries(url, attempts=3):
    """Try the feed directly, then the relay a few times (it sometimes returns a 500)."""
    errors = []
    try:
        return read_feed(url)
    except Exception as error:
        errors.append(f"direct: {error}")
    for attempt in range(attempts):
        try:
            return read_feed_via_relay(url)
        except Exception as error:
            errors.append(f"relay: {error}")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("; ".join(errors))


def previous_posts():
    """The posts the live site showed last time, so a failed feed doesn't empty a writer's posts."""
    try:
        return json.loads(fetch(PREVIOUS))
    except Exception as error:
        print(f"::warning::could not load previous posts ({error})")
        return []


def main():
    posts = []
    previous = None
    for path in sorted((ROOT / "_members").glob("*.md")):
        fields = front_matter(path)
        url = feed_url(fields)
        if not url:
            continue
        try:
            posts += to_posts(fetch_with_retries(url), path.stem, fields["hide"], fields["mute"])
            print(f"{path.stem}: ok")
        except Exception as error:
            if previous is None:
                previous = previous_posts()
            kept = [
                dict(post, muted=post["title"].lower() in fields["mute"] or post["url"].rstrip("/").lower() in fields["mute"])
                for post in previous
                if post.get("author") == path.stem
                and post["title"].lower() not in fields["hide"]
                and post["url"].rstrip("/").lower() not in fields["hide"]
            ]
            posts += kept
            # "::warning::" makes the message show up on the GitHub Actions run.
            print(f"::warning::{path.stem}: feed failed ({error}); kept {len(kept)} posts from the live site")

    posts.sort(key=lambda post: post["date"], reverse=True)
    out = ROOT / "_data" / "feed.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(posts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(posts)} posts written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
