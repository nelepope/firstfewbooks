"""Read events from the members' Google Sheet and write _data/sheet_events.json.

The sheet must be published to the web as CSV (File > Share > Publish to web > CSV);
put that link in _config.yml as events_sheet_csv. Columns are matched by their
headings, so the form's question wording can change. Rows without a title or a
date we can read are skipped. If the sheet can't be loaded, the file is left
empty and the site still builds.
"""

import csv
import io
import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Heading keyword -> event field. The first heading containing a keyword wins.
COLUMNS = [
    ("end", "end_date"), ("until", "end_date"), ("last", "end_date"),
    ("title", "title"), ("event name", "title"), ("what", "title"),
    ("date", "date"), ("when", "date"),
    ("time", "time"),
    ("place", "place"), ("location", "place"), ("where", "place"), ("venue", "place"),
    ("description", "description"), ("about", "description"), ("details", "description"),
    ("link", "url"), ("url", "url"), ("ticket", "url"), ("website", "url"),
    ("host", "host"), ("organis", "host"), ("your name", "host"), ("who", "host"),
    ("show", "show"), ("approved", "show"),
]
DATE_FORMATS = ["%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y", "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%d.%m.%Y"]


def sheet_url():
    config = (ROOT / "_config.yml").read_text(encoding="utf-8")
    m = re.search(r"^events_sheet_csv:[ \t]*[\"']?([^\s\"']+)", config, re.M)
    return m.group(1) if m else None


def parse_date(value):
    value = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", (value or "").strip())
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def map_headings(headings):
    mapping = {}
    for field_keyword, field in COLUMNS:
        if field in mapping.values():
            continue
        for i, heading in enumerate(headings):
            if i not in mapping and field_keyword in heading.lower() and heading.lower() != "timestamp":
                mapping[i] = field
                break
    return mapping


def main():
    out = ROOT / "_data" / "sheet_events.json"
    out.parent.mkdir(exist_ok=True)
    events = []
    url = sheet_url()
    if url:
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                rows = list(csv.reader(io.StringIO(response.read().decode("utf-8"))))
            mapping = map_headings(rows[0])
            for row in rows[1:]:
                event = {field: row[i].strip() for i, field in mapping.items() if i < len(row) and row[i].strip()}
                if event.pop("show", "yes").lower() in ("no", "n", "false", "hide"):
                    continue
                event["date"] = parse_date(event.get("date"))
                if "end_date" in event:
                    event["end_date"] = parse_date(event["end_date"])
                    if not event["end_date"]:
                        del event["end_date"]
                if event.get("title") and event["date"]:
                    events.append(event)
                else:
                    print(f"::warning::events sheet: skipped a row (needs a title and a date like 14/11/2026): {row}")
        except Exception as error:
            print(f"::warning::events sheet could not be read ({error})")
    out.write_text(json.dumps(events, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(events)} events written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
