"""Load site/content.toml and resolve translations.

A translated value is a table whose keys are all language codes, e.g.
``{ en = "Work", it = "Progetti" }``. Every other value is shared by all
languages. ``localize`` turns the whole tree into plain values for one
language; ``validate`` fails loudly when a translation is incomplete, so a
missing string breaks the build instead of shipping an empty label.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


class ContentError(ValueError):
    """Raised when content.toml is malformed or incomplete."""


def load(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        data = tomllib.load(f)
    validate(data)
    return data


def _is_translation(value: Any, languages: list[str]) -> bool:
    return isinstance(value, dict) and bool(value) and set(value) <= set(languages)


def _walk_translations(node: Any, languages: list[str], where: str, errors: list[str]) -> None:
    if _is_translation(node, languages):
        missing = [lang for lang in languages if lang not in node]
        if missing:
            errors.append(f"{where}: missing {', '.join(missing)}")
        return
    if isinstance(node, dict):
        for key, value in node.items():
            _walk_translations(value, languages, f"{where}.{key}" if where else key, errors)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            _walk_translations(value, languages, f"{where}[{i}]", errors)


def validate(data: dict[str, Any]) -> None:
    languages = data.get("languages")
    if not languages or data.get("default_language") not in languages:
        raise ContentError("`languages` must list `default_language`")

    errors: list[str] = []
    ui = data.get("ui", {})
    keys = [set(ui.get(lang, {})) for lang in languages]
    for lang, lang_keys in zip(languages, keys):
        for missing in sorted(set().union(*keys) - lang_keys):
            errors.append(f"ui.{lang}: missing key {missing!r}")

    content = {k: v for k, v in data.items() if k != "ui"}
    _walk_translations(content, languages, "", errors)

    slugs = [p["slug"] for p in data.get("projects", [])]
    if len(slugs) != len(set(slugs)):
        errors.append("projects: duplicate slug")
    for exp in data.get("experience", []):
        if "link" in exp and exp["link"] not in slugs:
            errors.append(f"experience: link to unknown project {exp['link']!r}")
    for project in data.get("projects", []):
        for link in project.get("links", []):
            if link.get("kind") not in {"code", "paper", "thesis"}:
                errors.append(f"projects.{project['slug']}: unknown link kind {link.get('kind')!r}")

    if errors:
        raise ContentError("content.toml is invalid:\n  " + "\n  ".join(errors))


def localize(node: Any, lang: str, languages: list[str]) -> Any:
    """Return a copy of ``node`` with every translation resolved to ``lang``."""
    if _is_translation(node, languages):
        return node[lang]
    if isinstance(node, dict):
        return {k: localize(v, lang, languages) for k, v in node.items()}
    if isinstance(node, list):
        return [localize(v, lang, languages) for v in node]
    return node
