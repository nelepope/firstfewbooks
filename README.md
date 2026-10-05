# First Few Books

The website for the First Few Books writing group, at [firstfewbooks.com](https://firstfewbooks.com).

It's built with Jekyll, which GitHub Pages runs automatically. Every change pushed to `main` goes live within a minute or two.

## Blog posts

Posts aren't written on this site. They're pulled in from each member's Substack every 6 hours, and every card links out to the post on Substack. Give a member a `substack:` line (below) and their posts will appear on the home page, the blog page and their profile.

For a blog that isn't on Substack, use `feed:` with the full RSS address instead (for example `feed: https://example.wordpress.com/feed`).

To pull in new posts straight away, go to the repo's **Actions** tab, choose **Build and deploy** and click **Run workflow**.

## Add a member

Create `_members/jane-smith.md`:

```markdown
---
name: Jane Smith
tagline: Writing a debut crime novel.
substack: https://janesmith.substack.com
photo: /assets/images/members/jane-smith.jpg   # optional; initials are shown otherwise
links:
  - label: Website
    url: https://janesmith.com
featured:
  - title: A short story
    url: https://magazine.com/story
    where: Some Magazine
    note: One line about it.
---

A short bio.
```

## Add a book to the shop

Create `_books/book-title.md`:

```markdown
---
title: The Book Title
author: jane-smith
date: 2027-03-01          # publication date; newest show first
blurb: One or two lines.
price: £12.99
buy_url: https://...      # leave out to show "Coming soon"
cover: /assets/images/books/book-title.jpg   # optional
---
```

The shop links out to wherever each book is sold (Bookshop.org, the publisher, Amazon), so there's no checkout to run.

## Change the look

Colours and fonts are set at the top of `assets/css/style.css`.

## Preview locally

```bash
python3 scripts/fetch_feeds.py && ~/.gem/ruby/2.6.0/bin/jekyll serve
```

Then open http://localhost:4000.
