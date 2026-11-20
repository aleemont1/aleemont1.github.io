# aleemont.dev

My portfolio. A small Python generator turns `site/content.toml` into a static site
in English (`/`) and Italian (`/it/`), with a case-study page for each featured project.
GitHub Actions builds and deploys it on every push to `main`, and once a day to refresh
the activity heatmap and the latest posts from [blog.aleemont.dev](https://blog.aleemont.dev).

## Layout

| Path | What it is |
|---|---|
| `site/content.toml` | All the text: projects, experience, documents, interface strings, in both languages |
| `site/templates/` | Jinja templates (`index.html`, `work.html` for case studies, `_macros.html` for diagrams and charts) |
| `site/assets/` | Stylesheet, favicon, self-hosted fonts (Inter and JetBrains Mono, OFL) |
| `site/icons/` | [Phosphor](https://phosphoricons.com) icons (MIT), inlined at build time |
| `src/build.py` | The build: renders every page, sitemap, robots.txt and 404 |
| `src/activity.py` | GitHub contribution calendar → inline SVG in the site's palette |
| `src/feed.py` | Latest posts from the blog's RSS feed |
| `src/seo.py` | JSON-LD, `robots.txt` (keeps the CVs out of search) and `/llms.txt` |
| `site/assets/og/` | 1200×630 preview images for shared links |
| `tests/` | Unit tests and fixtures; CI runs them before every build |

## Editing content

Every text field is either a plain string or a table with one entry per language:

```toml
title = { en = "Selected work", it = "Progetti principali" }
```

The build fails if a translation is missing. A project with a `[projects.detail]` table
gets its own page at `/work/<slug>/`.

## Running locally

```sh
pip install -r requirements.txt
python -m unittest discover -s tests -t .
python -m src.build --out _site --offline \
  --activity-json tests/fixtures/contributions.json --feed-xml tests/fixtures/rss.xml
python -m http.server -d _site 8000
```

Without `--offline` the build calls the GitHub GraphQL API (needs `GITHUB_TOKEN`) and the
blog's feed. If either fails, that section is left out and the build still succeeds.

## Deployment

Settings → Pages → Source must be **GitHub Actions**. The custom domain is set there too;
`CNAME` is copied into the build for reference.
