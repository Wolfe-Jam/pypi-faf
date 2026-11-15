"""Render docs/index.html from PyPI + pypistats + packages.yml overlay.

Auto-discovers packages by scraping pypi.org/user/wolfejam/.
Live stats from pypistats (without_mirrors only — public-count doctrine).
Curated overlay (role, Zenodo, badge, pinned) from packages.yml.

Run: uv run python build/render.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
OUT = ROOT / "docs" / "index.html"
SITEMAP = ROOT / "docs" / "sitemap.xml"
OVERLAY = ROOT / "packages.yml"
BASELINE_FILE = ROOT / "build" / "baseline.json"

PYPI_USER = "wolfejam"
USER_AGENT = "pypi-faf-renderer/0.1 (+https://pypi.faf.one)"

# pypistats keeps ~180 days of daily rows. A baseline older than this many days
# may have days that already fell out of the window: refuse rather than undercount.
MAX_BASELINE_AGE_DAYS = 170

# pypistats rate-limits aggressively. Pace between calls + retry with backoff.
PYPISTATS_DELAY = 2.0           # seconds between successful calls
PYPISTATS_BACKOFF = [10, 20, 40]  # seconds before each retry on 429


def discover_packages(client: httpx.Client) -> list[str]:
    """Scrape pypi.org/user/<user>/ for the package name list."""
    r = client.get(f"https://pypi.org/user/{PYPI_USER}/")
    r.raise_for_status()
    names = re.findall(r'<h3 class="package-snippet__title">\s*<span class="package-snippet__name">([^<]+)</span>', r.text)
    return sorted(set(names))


def fetch_pypi_meta(client: httpx.Client, pkg: str) -> dict:
    r = client.get(f"https://pypi.org/pypi/{pkg}/json")
    r.raise_for_status()
    info = r.json()["info"]
    return {
        "version": info.get("version", ""),
        "summary": (info.get("summary") or "").strip(),
        "home_page": info.get("home_page") or info.get("project_url") or f"https://pypi.org/project/{pkg}/",
    }


def fetch_stats(client: httpx.Client, pkg: str) -> dict:
    """Daily rows + last-7d downloads, without_mirrors only. Retries 429 with backoff."""
    url = f"https://pypistats.org/api/packages/{pkg}/overall"
    for attempt in range(len(PYPISTATS_BACKOFF) + 1):
        if attempt > 0:
            delay = PYPISTATS_BACKOFF[attempt - 1]
            print(f"    ↻ 429 — backoff {delay}s (retry {attempt}/{len(PYPISTATS_BACKOFF)})", file=sys.stderr)
            time.sleep(delay)
        r = client.get(url)
        if r.status_code == 429:
            continue
        r.raise_for_status()
        rows = [row for row in r.json().get("data", []) if row.get("category") == "without_mirrors"]
        days = {row["date"]: row["downloads"] for row in rows}
        cutoff = (date.today() - timedelta(days=8)).isoformat()
        weekly = sum(n for d, n in days.items() if d >= cutoff)
        return {"days": days, "weekly": weekly}
    print(f"  ! pypistats 429 for {pkg} after {len(PYPISTATS_BACKOFF)} retries — loud-fail, refuse zero", file=sys.stderr)
    sys.exit(2)


def load_overlay() -> dict[str, dict]:
    if not OVERLAY.exists():
        return {}
    data = yaml.safe_load(OVERLAY.read_text())
    return {p["name"]: p for p in data.get("packages", [])}


class BaselineError(Exception):
    pass


def load_baselines() -> dict[str, dict]:
    """Per package: {"total": all-time downloads, "through": last day counted}.

    pypistats /overall only keeps ~180 days, so its sum is not an all-time
    total once a package is older than that. The all-time total is kept here
    instead: baseline + the days after it, and the result becomes the next
    baseline. The first baselines (through 2026-11-14) were counted from the
    public PyPI dataset on BigQuery with pypistats' own mirror rule (see
    build/seed.sql).
    """
    if not BASELINE_FILE.exists():
        return {}
    return json.loads(BASELINE_FILE.read_text())


def save_baselines(baselines: dict[str, dict]) -> None:
    BASELINE_FILE.write_text(json.dumps(baselines, indent=2, sort_keys=True) + "\n")


def advance(base: dict | None, days: dict[str, int], today: date) -> dict:
    """Add the days after base["through"] to base["total"]; return the new baseline."""
    if base is None:
        # New package: its whole history is still inside the pypistats window.
        if not days:
            return {"total": 0, "through": (today - timedelta(days=1)).isoformat()}
        return {"total": sum(days.values()), "through": max(days)}
    through = base["through"]
    age = (today - date.fromisoformat(through)).days
    if age > MAX_BASELINE_AGE_DAYS:
        raise BaselineError(
            f"baseline is {age} days old (through {through}); days may have left the "
            f"pypistats window. Reseed from BigQuery (build/seed.sql)."
        )
    new = sum(n for d, n in days.items() if d > through)
    return {"total": base["total"] + new, "through": max([through, *days])}


def build_records(client: httpx.Client, baselines: dict[str, dict]) -> list[dict]:
    discovered = discover_packages(client)
    overlay = load_overlay()
    overlay_names = set(overlay.keys())

    # Surface any package on PyPI not yet curated.
    new = [n for n in discovered if n not in overlay_names]
    if new:
        print(f"  ! discovered (not yet in packages.yml): {', '.join(new)}", file=sys.stderr)

    names = sorted(set(discovered) | overlay_names)
    records = []
    pending: dict[str, dict] = {}   # only saved if the whole run passes
    empty = 0

    for i, name in enumerate(names):
        if i > 0:
            time.sleep(PYPISTATS_DELAY)
        print(f"  · {name}")
        meta = fetch_pypi_meta(client, name)
        stats = fetch_stats(client, name)
        cur = overlay.get(name, {})

        if not stats["days"]:
            empty += 1
        if name not in baselines:
            print(f"  ! {name}: no baseline; counting from pypistats' window. "
                  f"If it is older than ~180 days, seed it from BigQuery.", file=sys.stderr)
        try:
            pending[name] = advance(baselines.get(name), stats["days"], date.today())
        except BaselineError as e:
            print(f"\n✗ FATAL: {name}: {e}", file=sys.stderr)
            sys.exit(3)

        records.append({
            "name": name,
            "version": meta["version"],
            "role": cur.get("role") or meta["summary"] or "—",
            "zenodo": cur.get("zenodo"),
            "badge": cur.get("badge"),
            "pinned": bool(cur.get("pinned")),
            "total": pending[name]["total"],
            "weekly": stats["weekly"],
        })

    # No daily rows for most packages at once = a pypistats outage or schema
    # change, not a quiet week. Refuse to write: the last-good page stays live
    # and the footer date stops moving, so the staleness shows.
    if empty > len(records) // 2:
        print(
            f"\n✗ FATAL: {empty}/{len(records)} packages returned no daily rows. "
            f"Likely pypistats outage or schema change. Refusing to write a new "
            f"docs/index.html — last-good stays live; footer date will show staleness.",
            file=sys.stderr,
        )
        sys.exit(3)

    baselines.update(pending)

    # Sort: pinned first, then by total desc.
    records.sort(key=lambda r: (not r["pinned"], -r["total"]))
    return records


def render(records: list[dict]) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["comma"] = lambda n: f"{n:,}"
    template = env.get_template("index.html.j2")
    return template.render(
        packages=records,
        total_packages=len(records),
        total_downloads=sum(r["total"] for r in records),
        weekly_downloads=sum(r["weekly"] for r in records),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    )


def write_sitemap() -> None:
    """Single-URL sitemap; lastmod tracks today so crawlers know to recheck."""
    today = date.today().isoformat()
    SITEMAP.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '  <url>\n'
        '    <loc>https://pypi.faf.one/</loc>\n'
        f'    <lastmod>{today}</lastmod>\n'
        '    <changefreq>daily</changefreq>\n'
        '    <priority>1.0</priority>\n'
        '  </url>\n'
        '</urlset>\n'
    )


def main() -> None:
    baselines = load_baselines()
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30.0) as client:
        records = build_records(client, baselines)
    html = render(records)
    OUT.write_text(html)
    save_baselines(baselines)
    write_sitemap()
    print(f"  ✓ wrote {OUT.relative_to(ROOT)} ({len(records)} packages)")
    print(f"  ✓ updated {BASELINE_FILE.relative_to(ROOT)} ({len(baselines)} baselines)")
    print(f"  ✓ wrote {SITEMAP.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
