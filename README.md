# First Few Books

The website for the First Few Books writing group, at [firstfewbooks.com](https://firstfewbooks.com).

It's built with Jekyll, which GitHub Pages runs automatically. Every change pushed to `main` goes live within a minute or two.

## Add a blog post

Create a file in `_posts/` named `YYYY-MM-DD-short-title.md`:

```markdown
---
title: What we learned from our first critique night
author: jane-smith
---

The first paragraph becomes the preview on the home page.

The rest of the post goes here.
```

`author` must match the member's filename in `_members/` (without `.md`). The post then appears on the blog, on the home page if it's one of the three newest, and on that member's profile.

## Add a member

Create `_members/jane-smith.md`:

```markdown
---
name: Jane Smith
tagline: Writing a debut crime novel.
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
~/.gem/ruby/2.6.0/bin/jekyll serve
```

Then open http://localhost:4000.
