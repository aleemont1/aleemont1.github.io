"""Search and answer-engine metadata: JSON-LD, robots.txt and /llms.txt.

Everything here is derived from content.toml, so the structured data can only
say what the visible page already says.
"""

from __future__ import annotations

from typing import Any


def _person_id(site_url: str) -> str:
    return f"{site_url}/#person"


def person(c: dict[str, Any]) -> dict[str, Any]:
    site, seo = c["site"], c["seo"]
    return {
        "@type": "Person",
        "@id": _person_id(site["url"]),
        "name": site["name"],
        "url": site["url"] + "/",
        "jobTitle": site["role"],
        "description": site["description"],
        "sameAs": seo["same_as"],
        "alumniOf": {"@type": "CollegeOrUniversity", "name": seo["alumni_of"]},
        **({"worksFor": {"@type": "Organization", "name": seo["works_for"]}} if seo.get("works_for") else {}),
        "knowsAbout": seo["knows_about"],
    }


def website(c: dict[str, Any]) -> dict[str, Any]:
    site = c["site"]
    return {
        "@type": "WebSite",
        "@id": f"{site['url']}/#website",
        "url": site["url"] + "/",
        "name": site["name"],
        "author": {"@id": _person_id(site["url"])},
    }


def home(c: dict[str, Any], url: str, lang: str) -> dict[str, Any]:
    site = c["site"]
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "ProfilePage",
                "@id": url,
                "url": url,
                "name": f"{site['name']} · {site['role']}",
                "inLanguage": lang,
                "mainEntity": {"@id": _person_id(site["url"])},
            },
            person(c),
            website(c),
        ],
    }


def project(c: dict[str, Any], p: dict[str, Any], url: str, home_url: str, lang: str) -> dict[str, Any]:
    site = c["site"]
    detail = p["detail"]
    code = [link["url"] for link in p.get("links", []) if link["kind"] == "code"]
    work: dict[str, Any] = {
        "@type": ["CreativeWork", "SoftwareSourceCode"] if code else "CreativeWork",
        "@id": url,
        "url": url,
        "name": p["title"],
        "headline": f"{p['title']}: {p['subtitle']}",
        "description": detail.get("seo_description", p["summary"]),
        "inLanguage": lang,
        "image": site["url"] + detail.get("og_image", site["og_image"]),
        "author": {"@id": _person_id(site["url"])},
        "isPartOf": {"@id": f"{site['url']}/#website"},
        "mainEntityOfPage": url,
        "keywords": p["stack"],
    }
    if code:
        work["codeRepository"] = code[0]
    return {
        "@context": "https://schema.org",
        "@graph": [
            work,
            person(c),
            website(c),
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": site["name"], "item": home_url},
                    {"@type": "ListItem", "position": 2, "name": p["title"], "item": url},
                ],
            },
        ],
    }


def robots(site_url: str, noindex_paths: list[str]) -> str:
    """Block everything under each path except its landing page.

    The landing page carries <meta name="robots" content="noindex">, which a
    crawler can only see if it may fetch the page; the PDFs and previews
    can't carry it, so they are blocked instead. The longest matching rule
    wins, so "Allow: /x/$" beats "Disallow: /x/" for the landing page only.
    """
    rules = [line for path in noindex_paths for line in (f"Disallow: {path}", f"Allow: {path}$")]
    lines = ["User-agent: *", *rules, "Allow: /", "", f"Sitemap: {site_url}/sitemap.xml", ""]
    return "\n".join(lines)


def llms_txt(c: dict[str, Any], other_lang_url: str | None) -> str:
    """A plain-markdown summary of the site for LLM-based tools (llmstxt.org)."""
    site = c["site"]
    out = [f"# {site['name']}", "", f"> {site['description']}", ""]
    out += [para for para in c["intro"]["body"] for para in (para, "")]

    out += ["## Projects", ""]
    for p in c["projects"]:
        if "detail" in p:
            desc = p["detail"].get("seo_description", p["summary"])
            out.append(f"- [{p['title']}]({site['url']}/work/{p['slug']}/): {desc}")
    out += ["", "## Other projects", ""]
    for p in c["projects"]:
        if "detail" not in p:
            links = "".join(f" [{link['kind']}]({link['url']})" for link in p.get("links", []))
            out.append(f"- {p['title']} ({p['subtitle']}): {p['summary']}{links}")

    out += ["", "## Experience", ""]
    out += [f"- {e['period']}: {e['role']}, {e['org']}. {e['text']}" for e in c["experience"]]
    out += ["", "## Education", ""]
    out += [f"- {e['period']}: {e['title']}, {e['org']}" for e in c["education"]]

    out += ["", "## Optional", ""]
    out += [f"- [{d['title']}]({d['url']}): {d['text']}" for d in c["documents"]
            if not any(path in d["url"] for path in c["seo"]["noindex_paths"])]
    out += [f"- [GitHub]({site['github']})", f"- [LinkedIn]({site['linkedin']})", f"- [Blog]({site['blog']})"]
    if other_lang_url:
        out.append(f"- [Italian version]({other_lang_url})")
    return "\n".join(out) + "\n"
