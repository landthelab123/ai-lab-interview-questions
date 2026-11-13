#!/usr/bin/env python3
"""Rebuild this repo's pages from Land the Lab's public data.

Standard library only. Writes README.md and companies/<slug>.md.
Run: python3 scripts/build.py
"""

from __future__ import annotations

import json
import time
import urllib.request
from datetime import date
from pathlib import Path

API = "https://api.landthelab.com/api/web"
SITE = "https://landthelab.com"
ROOT = Path(__file__).resolve().parent.parent
UA = "landthelab-index/1.0 (+https://landthelab.com)"

ROUND_ORDER = [
    "recruiter_screen", "oa", "phone_screen", "practical", "coding",
    "system_design", "ml_design", "project_deep_dive", "hiring_manager",
    "behavioral", "culture", "onsite", "other",
]


def get(path: str) -> dict:
    req = urllib.request.Request(f"{API}{path}", headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def cell(text: str | None) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def question_url(slug: str) -> str:
    return f"{SITE}/questions/{slug}"


def company_page(d: dict, round_names: dict[str, str]) -> str:
    c = d["company"]
    name = c["name"]
    url = f"{SITE}/companies/{c['slug']}"
    counts = d.get("counts") or {}
    questions = [q for q in d.get("questions") or [] if not q.get("retired")]
    out = [f"# {name} interview questions and loop ({date.today().year})", ""]
    if c.get("formerly"):
        out += [f"*Formerly {c['formerly']}.*", ""]
    line = f"{len(questions)} engineering interview questions candidates report from {name}"
    if counts.get("last_reported"):
        line += f", most recently in {counts['last_reported']}"
    out += [line + f". Worked answers, a rubric per level and a prep plan: **[{name} on Land the Lab]({url})**.", ""]

    loop = d.get("loop") or {}
    if loop.get("summary"):
        out += ["## The loop", "", loop["summary"], ""]
    rounds = d.get("rounds") or []
    if rounds:
        out += ["| # | Round | Length | Format |", "|---|---|---|---|"]
        for i, r in enumerate(rounds, 1):
            mins = f"{r['minutes']} min" if r.get("minutes") else ""
            out.append(f"| {i} | {cell(r.get('name'))} | {mins} | {cell(r.get('format'))} |")
        out += ["", f"What each round grades, its AI policy and how to prep: [{name} interview process]({url}).", ""]

    by_round: dict[str, list[dict]] = {}
    for q in questions:
        by_round.setdefault(q.get("round") or "other", []).append(q)
    order = [r["key"] for r in rounds if r.get("key") in by_round]
    order += [k for k in ROUND_ORDER if k in by_round and k not in order]
    order += [k for k in by_round if k not in order]

    out += ["## Questions by round", ""]
    for key in order:
        qs = sorted(by_round[key], key=lambda q: q.get("last_asked_on") or "", reverse=True)
        label = round_names.get(key) or key.replace("_", " ").capitalize()
        out += [f"### {label}", "", "| Question | Type | How often | Last asked |", "|---|---|---|---|"]
        for q in qs:
            out.append(
                f"| [{cell(q['title'])}]({question_url(q['slug'])}) | {cell(q.get('kind_label'))} "
                f"| {cell(q.get('frequency_label'))} | {cell(q.get('asked'))} |"
            )
        out.append("")
    out += ["---", "", f"Updated {date.today().isoformat()} from [Land the Lab]({SITE}). Back to [all companies](../README.md).", ""]
    return "\n".join(out)


def main() -> None:
    sitemap = get("/sitemap")
    slugs = [c["slug"] for c in sitemap["companies"]]
    (ROOT / "companies").mkdir(exist_ok=True)
    rows = []
    round_names: dict[str, str] = {}
    pages = {}
    for slug in slugs:
        d = get(f"/pages/companies/{slug}")
        pages[slug] = d
        for r in d.get("rounds") or []:
            if r.get("key") and r.get("name"):
                round_names.setdefault(r["key"], r["name"])
        time.sleep(0.3)
    for slug, d in pages.items():
        qs = [q for q in d.get("questions") or [] if not q.get("retired")]
        if not qs:
            continue
        (ROOT / "companies" / f"{slug}.md").write_text(company_page(d, round_names))
        c = d["company"]
        rows.append((len(qs), c["name"], slug, (d.get("counts") or {}).get("last_reported") or "", len(d.get("rounds") or [])))
    rows.sort(key=lambda r: (-r[0], r[1].lower()))
    total = sum(r[0] for r in rows)
    groups = get("/pages/questions").get("company_groups") or []
    group_of = {c["slug"]: g["label"] for g in groups for c in g.get("companies") or []}
    labels = [g["label"] for g in groups] + ["More companies"]

    readme = [
        "# AI lab interview questions (2026)",
        "",
        f"{total} real engineering interview questions from {len(rows)} AI labs and top tech companies — OpenAI, "
        "Anthropic, Google DeepMind, SpaceXAI and more — by company and round, with how often each is asked "
        "and when it was last reported. Updated every week.",
        "",
        f"Each question links to its page on **[Land the Lab]({SITE})**, with a worked answer, a rubric for "
        "L4/L5/L6 and an AI coach that grades your own attempt.",
        "",
    ]
    for label in labels:
        group_rows = [r for r in rows if group_of.get(r[2], "More companies") == label]
        if not group_rows:
            continue
        readme += [f"## {label}", "", "| Company | Questions | Rounds in the loop | Last reported |", "|---|---|---|---|"]
        for n, name, slug, last, nrounds in group_rows:
            readme.append(f"| [{cell(name)}](companies/{slug}.md) | {n} | {nrounds or ''} | {last} |")
        readme.append("")
    readme += [
        "",
        "## What's here",
        "",
        "- **The loop** for each company: its rounds in order, how long each takes and its format.",
        "- **Questions by round**: coding, system design, ML design, practical and behavioral, newest first.",
        "- **Freshness**: how often a question comes up and the month it was last reported. Older than a year reads as possibly retired.",
        "",
        "Questions come from candidates' reports and are written up in our own words.",
        "",
        "## More",
        "",
        f"- [All questions]({SITE}/questions), searchable by company, round and date",
        f"- [AI engineer interview questions]({SITE}/ai-engineer-interview-questions)",
        f"- [Pricing]({SITE}/pricing): one free answer per company, or every answer with a plan",
        "",
        f"Updated {date.today().isoformat()}.",
        "",
    ]
    (ROOT / "README.md").write_text("\n".join(readme))
    print(f"{len(rows)} companies, {total} questions")


if __name__ == "__main__":
    main()
