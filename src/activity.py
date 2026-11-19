"""GitHub contribution calendar, drawn as an inline SVG in the site's palette.

The data comes from the GraphQL API (the Actions ``GITHUB_TOKEN`` is enough).
Cells carry a level class (``l0``..``l4``) and the colours live in the
stylesheet, so the heatmap follows the light/dark theme like everything else.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from dataclasses import dataclass
from html import escape

import requests

log = logging.getLogger(__name__)

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""

LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

CELL = 11  # px, square side
GAP = 3  # px between cells
TOP = 18  # px reserved for month labels

MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "it": ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"],
}


@dataclass(frozen=True)
class Day:
    date: dt.date
    count: int
    level: int


@dataclass(frozen=True)
class Calendar:
    total: int
    weeks: list[list[Day]]


def fetch(login: str, token: str, timeout: float = 20) -> dict:
    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": QUERY, "variables": {"login": login}},
        headers={"Authorization": f"bearer {token}"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(json.dumps(payload["errors"]))
    return payload


def parse(payload: dict) -> Calendar:
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [
        [
            Day(
                date=dt.date.fromisoformat(d["date"]),
                count=int(d["contributionCount"]),
                level=LEVELS.get(d["contributionLevel"], 0),
            )
            for d in week["contributionDays"]
        ]
        for week in cal["weeks"]
    ]
    return Calendar(total=int(cal["totalContributions"]), weeks=[w for w in weeks if w])


def _format_date(day: dt.date, lang: str) -> str:
    month = MONTHS[lang][day.month - 1]
    return f"{month} {day.day}, {day.year}" if lang == "en" else f"{day.day} {month} {day.year}"


def _cell_label(day: Day, ui: dict, lang: str) -> str:
    date = _format_date(day.date, lang)
    if day.count == 0:
        return ui["contributions_cell_none"].format(date=date)
    if day.count == 1:
        return ui["contributions_cell_one"].format(date=date)
    return ui["contributions_cell"].format(n=day.count, date=date)


def render_svg(calendar: Calendar, ui: dict, lang: str) -> str:
    """Return the heatmap as an SVG string (weeks are columns, Sunday on top)."""
    step = CELL + GAP
    width = len(calendar.weeks) * step - GAP
    height = TOP + 7 * step - GAP
    parts = [
        f'<svg class="heatmap" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-label="{escape(ui["contributions"].format(n=calendar.total))}">'
    ]

    last_month = None
    for x, week in enumerate(calendar.weeks):
        first = week[0].date
        # Label a month on the first full week that starts in it, if there is room.
        if first.month != last_month and first.day <= 7 and x < len(calendar.weeks) - 2:
            parts.append(
                f'<text class="hm-month" x="{x * step}" y="11">{MONTHS[lang][first.month - 1]}</text>'
            )
            last_month = first.month
        for day in week:
            y = TOP + ((day.date.weekday() + 1) % 7) * step  # Sunday = row 0, as on GitHub
            parts.append(
                f'<rect class="l{day.level}" x="{x * step}" y="{y}" width="{CELL}" height="{CELL}" rx="2">'
                f"<title>{escape(_cell_label(day, ui, lang))}</title></rect>"
            )
    parts.append("</svg>")
    return "".join(parts)


def load(login: str, token: str | None, cached: str | None = None) -> Calendar | None:
    """Fetch the calendar, or read it from a JSON file. Returns None on failure:
    the section is then left out instead of failing the whole build."""
    try:
        if cached:
            with open(cached, encoding="utf-8") as f:
                return parse(json.load(f))
        if not token:
            log.warning("No GITHUB_TOKEN: skipping the activity heatmap")
            return None
        return parse(fetch(login, token))
    except Exception as exc:  # network, auth or schema problems must not break the site
        log.warning("Activity heatmap unavailable: %s", exc)
        return None
