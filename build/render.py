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
HWM_FILE = ROOT / "build" / "last-totals.json"

PYPI_USER = "wolfejam"
USER_AGENT = "pypi-faf-renderer/0.1 (+https://pypi.faf.one)"

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
    """Total + last-7d downloads, without_mirrors only. Retries 429 with backoff."""
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
        total = sum(row["downloads"] for row in rows)
        cutoff = (date.today() - timedelta(days=8)).isoformat()
        weekly = sum(row["downloads"] for row in rows if row.get("date", "") >= cutoff)
        return {"total": total, "weekly": weekly}
    print(f"  ! pypistats 429 for {pkg} after {len(PYPISTATS_BACKOFF)} retries — loud-fail, refuse zero", file=sys.stderr)
    sys.exit(2)


def load_overlay() -> dict[str, dict]:
    if not OVERLAY.exists():
        return {}
    data = yaml.safe_load(OVERLAY.read_text())
    return {p["name"]: p for p in data.get("packages", [])}


def load_hwm() -> dict[str, int]:
    """High-water marks: the last-known maximum total for each package.

    pypistats /overall has a ~180-day data window; once a package crosses that
    threshold, its earliest downloads silently fall off the sum, causing the
    "total" to decrease over time. The displayed total is max(current, HWM) so
    the visible number is monotonic by construction — never goes down.
    """
    if not HWM_FILE.exists():
        return {}
    return json.loads(HWM_FILE.read_text())


def save_hwm(hwm: dict[str, int]) -> None:
    HWM_FILE.write_text(json.dumps(hwm, indent=2, sort_keys=True) + "\n")


def build_records(client: httpx.Client, hwm: dict[str, int]) -> list[dict]:
    discovered = discover_packages(client)
    overlay = load_overlay()
    overlay_names = set(overlay.keys())

    # Surface any package on PyPI not yet curated.
    new = [n for n in discovered if n not in overlay_names]
    if new:
        print(f"  ! discovered (not yet in packages.yml): {', '.join(new)}", file=sys.stderr)

    names = sorted(set(discovered) | overlay_names)
    records = []
    pending_hwm: dict[str, int] = {}   # only commit if the render passes the validity threshold
    invalid_count = 0

    for i, name in enumerate(names):
        if i > 0:
            time.sleep(PYPISTATS_DELAY)
        print(f"  · {name}")
        meta = fetch_pypi_meta(client, name)
        stats = fetch_stats(client, name)
        cur = overlay.get(name, {})

        # Monotonic-total guarantee. Doctrine (wolfejam 2026-05-31):
        # totals NEVER go down. A miscounted lower-or-zero figure is INVALID,
        # not "natural data window shedding." Show the high-water mark and
        # refuse to elevate HWM on invalid input.
        fresh_total = stats["total"]
        last_known = hwm.get(name, 0)
        if last_known > 0 and fresh_total < last_known:
            print(
                f"  ✗ {name}: INVALID — pypistats returned {fresh_total}, HWM is {last_known}. "
                f"Refused; displaying HWM (delta {last_known - fresh_total}).",
                file=sys.stderr,
            )
            displayed_total = last_known
            invalid_count += 1
        else:
            displayed_total = fresh_total
            if fresh_total > last_known:
                pending_hwm[name] = fresh_total  # promote HWM only on valid increase

        records.append({
            "name": name,
            "version": meta["version"],
            "role": cur.get("role") or meta["summary"] or "—",
            "zenodo": cur.get("zenodo"),
            "badge": cur.get("badge"),
            "pinned": bool(cur.get("pinned")),
            "total": displayed_total,
            "weekly": stats["weekly"],
        })

    # Refuse-on-majority-invalid: if more than half the packages returned
    # invalid totals in one run, that's an API outage / bad-data event, not
    # natural drift. Refuse to write — last-good docs/index.html stays in
    # place, footer date stops moving, the staleness becomes visible.
    if invalid_count > len(records) // 2:
        print(
            f"\n✗ FATAL: {invalid_count}/{len(records)} packages returned INVALID totals "
            f"in one run. Likely pypistats outage or schema change. Refusing to write a "
            f"new docs/index.html — last-good stays live; footer date will show staleness.",
            file=sys.stderr,
        )
        sys.exit(3)

    # All clear — commit pending HWM updates.
    hwm.update(pending_hwm)

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
    hwm = load_hwm()
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30.0) as client:
        records = build_records(client, hwm)
    html = render(records)
    OUT.write_text(html)
    save_hwm(hwm)
    write_sitemap()
    print(f"  ✓ wrote {OUT.relative_to(ROOT)} ({len(records)} packages)")
    print(f"  ✓ updated {HWM_FILE.relative_to(ROOT)} ({len(hwm)} HWMs)")
    print(f"  ✓ wrote {SITEMAP.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
