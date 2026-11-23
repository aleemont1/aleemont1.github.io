import json
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from src import activity, build, content, feed

FIXTURES = Path(__file__).parent / "fixtures"


class ContentTest(unittest.TestCase):
    def test_real_content_is_valid(self):
        data = content.load(build.SITE / "content.toml")
        self.assertIn("en", data["languages"])

    def test_missing_translation_fails(self):
        data = {"languages": ["en", "it"], "default_language": "en",
                "hero": {"title": {"en": "Hello"}}}
        with self.assertRaisesRegex(content.ContentError, "hero.title: missing it"):
            content.validate(data)

    def test_missing_ui_key_fails(self):
        data = {"languages": ["en", "it"], "default_language": "en",
                "ui": {"en": {"a": "A", "b": "B"}, "it": {"a": "A"}}}
        with self.assertRaisesRegex(content.ContentError, "ui.it: missing key 'b'"):
            content.validate(data)

    def test_localize_resolves_nested_values(self):
        tree = {"t": {"en": "Work", "it": "Progetti"}, "list": [{"x": {"en": ["a"], "it": ["b"]}}], "n": 3}
        self.assertEqual(content.localize(tree, "it", ["en", "it"]),
                         {"t": "Progetti", "list": [{"x": ["b"]}], "n": 3})


class ActivityTest(unittest.TestCase):
    UI = {
        "contributions": "{n} contributions, {days} days",
        "contributions_cell": "{n} on {date}",
        "contributions_cell_one": "1 on {date}",
        "contributions_cell_none": "none on {date}",
    }

    def setUp(self):
        self.payload = json.loads((FIXTURES / "contributions.json").read_text())

    def test_parse_and_render(self):
        cal = activity.parse(self.payload)
        days = sum(len(w) for w in cal.weeks)
        svg = activity.render_svg(cal, self.UI, "en")
        self.assertEqual(svg.count("<rect"), days)
        self.assertIn(f'aria-label="{cal.total} contributions, {cal.active_days} days"', svg)
        self.assertRegex(svg, r'class="l[0-4]"')

    def test_sunday_is_first_row(self):
        cal = activity.parse(self.payload)
        sunday = next(d for d in cal.weeks[1] if d.date.weekday() == 6)
        svg = activity.render_svg(cal, self.UI, "en")
        label = activity._format_date(sunday.date, "en")
        rect = re.search(r'<rect [^>]*y="(\d+)"[^>]*><title>[^<]*' + re.escape(label), svg)
        self.assertEqual(int(rect.group(1)), activity.TOP)

    def test_failure_returns_none(self):
        self.assertIsNone(activity.load("someone", token=None))
        self.assertIsNone(activity.load("someone", token=None, cached="/does/not/exist.json"))


class FeedTest(unittest.TestCase):
    def test_parse_sorts_rebases_and_skips_untitled(self):
        posts = feed.parse((FIXTURES / "rss.xml").read_text(), "https://blog.aleemont.dev/")
        self.assertEqual([p.title for p in posts], ["Re-learning C without an IDE", "Older post"])
        self.assertEqual(posts[0].url, "https://blog.aleemont.dev/learning-c/")

    def test_unreachable_feed_is_empty(self):
        self.assertEqual(feed.load("https://blog.aleemont.dev", cached="/does/not/exist.xml"), [])


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "a" and attrs.get("href"):
            self.hrefs.append(attrs["href"])


class BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "site"
        cls.pages = build.build(cls.out, offline=True,
                                activity_json=str(FIXTURES / "contributions.json"),
                                feed_xml=str(FIXTURES / "rss.xml"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_pages_for_every_language(self):
        for page in ["index.html", "it/index.html", "work/aurora-rocketry/index.html", "it/work/lamp/index.html", "404.html"]:
            self.assertIn(page, self.pages)
        for extra in ["CNAME", "sitemap.xml", "robots.txt", "assets/style.css", "assets/favicon.svg"]:
            self.assertTrue((self.out / extra).exists(), extra)

    def test_languages_and_sections(self):
        en = (self.out / "index.html").read_text()
        it = (self.out / "it" / "index.html").read_text()
        self.assertIn('<html lang="en">', en)
        self.assertIn('<html lang="it">', it)
        self.assertIn("Altre cose che ho costruito", it)
        self.assertIn('class="heatmap"', en)
        self.assertIn("Re-learning C without an IDE", en)

    def test_internal_links_resolve(self):
        for rel in self.pages:
            parser = _Links()
            parser.feed((self.out / rel).read_text())
            for href in parser.hrefs:
                if not href.startswith("/"):
                    continue
                path, _, anchor = href.partition("#")
                target = self.out / path.lstrip("/")
                if path.endswith("/") or path == "":
                    target = target / "index.html"
                self.assertTrue(target.exists(), f"{rel}: broken link {href}")
                if anchor:
                    ids = _Links()
                    ids.feed(target.read_text())
                    self.assertIn(anchor, ids.ids, f"{rel}: missing anchor {href}")

    def test_images_exist_and_have_alt_text(self):
        for rel in self.pages:
            html = (self.out / rel).read_text()
            for tag in re.findall(r"<img [^>]*>", html):
                self.assertRegex(tag, r'alt="[^"]+"', f"{rel}: image without alt text")
                for src in re.findall(r'(/assets/img/[^" ,]+)', tag):
                    self.assertTrue((self.out / src.lstrip("/")).exists(), f"{rel}: missing {src}")

    def test_robots_hides_cvs_and_points_to_sitemap(self):
        robots = (self.out / "robots.txt").read_text()
        self.assertIn("Disallow: /curriculum-vitae/", robots)
        self.assertIn("Disallow: /one-page-cv/", robots)
        # The landing pages stay crawlable so their noindex meta is seen.
        self.assertIn("Allow: /curriculum-vitae/$", robots)
        self.assertIn("Allow: /one-page-cv/$", robots)
        self.assertIn("Sitemap: https://aleemont.dev/sitemap.xml", robots)

    def test_structured_data_and_previews(self):
        for rel in self.pages:
            html = (self.out / rel).read_text()
            image = re.search(r'<meta property="og:image" content="https://aleemont\.dev(/[^"]+)"', html)
            self.assertTrue(image and (self.out / image.group(1).lstrip("/")).exists(), f"{rel}: og:image")
            blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
            if rel == "404.html":
                self.assertEqual(blocks, [])
                self.assertIn('<meta name="robots" content="noindex">', html)
                continue
            self.assertEqual(len(blocks), 1, rel)
            graph = json.loads(blocks[0])["@graph"]
            person = next(n for n in graph if n["@type"] == "Person")
            self.assertEqual(person["name"], "Alessandro Monticelli")
            if "/work/" in rel:
                self.assertTrue(any(n["@type"] == "BreadcrumbList" for n in graph), rel)

    def test_titles_and_descriptions_fit_search_results(self):
        for rel in self.pages:
            if rel == "404.html":
                continue
            html = (self.out / rel).read_text()
            title = re.search(r"<title>(.*?)</title>", html).group(1)
            desc = re.search(r'<meta name="description" content="(.*?)">', html).group(1)
            self.assertLessEqual(len(title), 60, f"{rel}: title is {len(title)} characters")
            self.assertTrue(120 <= len(desc) <= 160, f"{rel}: description is {len(desc)} characters")
            for tag in ("twitter:title", "twitter:description"):
                self.assertIn(f'<meta name="{tag}"', html, f"{rel}: {tag}")

    def test_sitemap_has_lastmod_and_language_alternates(self):
        sitemap = (self.out / "sitemap.xml").read_text()
        self.assertEqual(sitemap.count("<url>"), 6)
        self.assertRegex(sitemap, r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>")
        self.assertIn('hreflang="it" href="https://aleemont.dev/it/work/lamp/"', sitemap)
        self.assertIn('hreflang="x-default" href="https://aleemont.dev/work/lamp/"', sitemap)

    def test_llms_txt_lists_projects_without_cvs(self):
        text = (self.out / "llms.txt").read_text()
        self.assertTrue(text.startswith("# Alessandro Monticelli"))
        self.assertIn("(https://aleemont.dev/work/lamp/)", text)
        self.assertNotIn("curriculum-vitae", text)
        self.assertNotIn("one-page-cv", text)

    def test_offline_build_drops_optional_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            build.build(Path(tmp), offline=True)
            html = (Path(tmp) / "index.html").read_text()
        self.assertNotIn('class="heatmap"', html)
        self.assertIn('id="writing"', html)


if __name__ == "__main__":
    unittest.main()
