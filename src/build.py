"""Build the portfolio into a static directory.

    python -m src.build --out _site
    python -m src.build --out _site --offline        # no network: no heatmap, no posts
    python -m src.build --activity-json f.json --feed-xml rss.xml   # local fixtures

Pages: / (English), /it/ (Italian), /work/<slug>/ and /it/work/<slug>/ for
projects with a case study, plus 404.html, sitemap.xml, robots.txt and llms.txt.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from . import activity, content, feed, seo

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

log = logging.getLogger("build")


def _icons() -> dict[str, Markup]:
    icons = {}
    for svg in (SITE / "icons").glob("*.svg"):
        markup = svg.read_text(encoding="utf-8").strip()
        markup = markup.replace("<svg ", '<svg class="ic" aria-hidden="true" focusable="false" ', 1)
        icons[svg.stem] = Markup(markup)
    return icons


def _number(value: float, lang: str) -> str:
    text = f"{value:g}"
    return text.replace(".", ",") if lang == "it" else text


def _prefix(lang: str, default: str) -> str:
    return "" if lang == default else f"/{lang}"


def _content_date() -> str | None:
    """Date of the last commit that touched the site's content or code (for <lastmod>)."""
    try:
        run = subprocess.run(["git", "log", "-1", "--format=%cs", "--", "site", "src"],
                             cwd=ROOT, capture_output=True, text=True, check=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return run.stdout.strip() or None


def _write(out: Path, rel: str, html: str) -> None:
    target = out / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    # Collapse the blank lines Jinja leaves behind; the HTML stays readable.
    target.write_text(re.sub(r"\n\s*\n+", "\n", html), encoding="utf-8")


def build(out: Path, offline: bool = False, activity_json: str | None = None,
          feed_xml: str | None = None) -> list[str]:
    data = content.load(SITE / "content.toml")
    languages: list[str] = data["languages"]
    default: str = data["default_language"]
    site = data["site"]

    if out.exists():
        shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)
    shutil.copytree(SITE / "assets", out / "assets", dirs_exist_ok=True)
    shutil.copy(ROOT / "CNAME", out / "CNAME")
    css_hash = hashlib.sha256((SITE / "assets" / "style.css").read_bytes()).hexdigest()[:10]

    calendar = None
    posts: list[feed.Post] = []
    if activity_json or not offline:
        calendar = activity.load(site["github_user"], os.getenv("GITHUB_TOKEN"), activity_json)
    if feed_xml or not offline:
        posts = feed.load(site["blog"], feed_xml)

    env = Environment(
        loader=FileSystemLoader(SITE / "templates"),
        autoescape=select_autoescape(["html", "xml"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals.update(icon=_icons(), css_hash=css_hash, languages=languages)

    detail_slugs = [p["slug"] for p in data["projects"] if "detail" in p]
    pages = ["/"] + [f"/work/{slug}/" for slug in detail_slugs]
    written: list[str] = []

    for lang in languages:
        c = content.localize({k: v for k, v in data.items() if k != "ui"}, lang, languages)
        ui = data["ui"][lang]
        prefix = _prefix(lang, default)
        other = [l for l in languages if l != lang]

        def alternates(path: str) -> dict[str, str]:
            return {l: site["url"] + _prefix(l, default) + path for l in languages}

        common = dict(
            c=c, ui=ui, lang=lang, prefix=prefix, default_language=default,
            other_lang=other[0] if other else None,
            other_prefix=_prefix(other[0], default) if other else "",
            num=lambda v, _lang=lang: _number(v, _lang),
        )

        heatmap = Markup(activity.render_svg(calendar, ui, lang)) if calendar else None
        home_url = alternates("/")[lang]
        html = env.get_template("index.html").render(
            **common, path="/", alternates=alternates("/"), heatmap=heatmap,
            calendar=calendar, posts=posts, jsonld=seo.home(c, home_url, lang),
        )
        rel = f"{prefix.lstrip('/')}/index.html".lstrip("/")
        _write(out, rel, html)
        written.append(rel)

        projects = [p for p in c["projects"] if "detail" in p]
        for i, project in enumerate(projects):
            path = f"/work/{project['slug']}/"
            html = env.get_template("work.html").render(
                **common, path=path, alternates=alternates(path), project=project,
                next_project=projects[(i + 1) % len(projects)] if len(projects) > 1 else None,
                jsonld=seo.project(c, project, alternates(path)[lang], home_url, lang),
            )
            rel = f"{prefix.lstrip('/')}{path}index.html".lstrip("/")
            _write(out, rel, html)
            written.append(rel)

    c = content.localize({k: v for k, v in data.items() if k != "ui"}, default, languages)
    common = dict(c=c, ui=data["ui"][default], lang=default, prefix="", default_language=default,
                  other_lang=None, other_prefix="", num=lambda v: _number(v, default))
    _write(out, "404.html", env.get_template("404.html").render(**common, path="/404", alternates={}, jsonld=None))
    written.append("404.html")

    # The home page changes every day (heatmap, latest posts); the case studies when the content does.
    changed = _content_date()
    today = datetime.now(timezone.utc).date().isoformat()
    urls = [
        {
            "loc": site["url"] + _prefix(l, default) + p,
            "lastmod": today if p == "/" and (calendar or posts) else changed,
            "alternates": {m: site["url"] + _prefix(m, default) + p for m in languages},
            "default": site["url"] + _prefix(default, default) + p,
        }
        for l in languages for p in pages
    ]
    sitemap = env.get_template("sitemap.xml").render(urls=urls)
    (out / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (out / "robots.txt").write_text(seo.robots(site["url"], data["seo"]["noindex_paths"]), encoding="utf-8")
    other = [l for l in languages if l != default]
    (out / "llms.txt").write_text(
        seo.llms_txt(c, f"{site['url']}{_prefix(other[0], default)}/" if other else None), encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    log.info("Wrote %d pages to %s (heatmap: %s, posts: %d)",
             len(written), out, "yes" if calendar else "no", len(posts))
    return written


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=ROOT / "_site")
    parser.add_argument("--offline", action="store_true", help="skip GitHub and blog requests")
    parser.add_argument("--activity-json", help="read the contribution calendar from this GraphQL response")
    parser.add_argument("--feed-xml", help="read blog posts from this RSS file")
    args = parser.parse_args()
    build(args.out, args.offline, args.activity_json, args.feed_xml)


if __name__ == "__main__":
    main()
