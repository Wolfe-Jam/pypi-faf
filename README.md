# pypi-faf

Sovereign landing page for **[pypi.faf.one](https://pypi.faf.one)** — FAF's PyPI showcase.

Auto-discovers packages published by [`wolfejam`](https://pypi.org/user/wolfejam/) and renders a single static HTML page. GH Pages serves it; `pypi.faf.one` CNAMEs here.

## How it works

```
pypi.org/user/wolfejam/       (discovery: package name list)
pypi.org/pypi/<pkg>/json      (per-package: version, summary)
pypistats.org/.../overall     (per-package: downloads, without_mirrors only)
packages.yml                  (curated overlay: role, Zenodo DOI, badge)
       ↓
build/render.py + templates/index.html.j2
       ↓
docs/index.html               (committed; served by GH Pages from /docs)
       ↓
pypi.faf.one
```

GitHub Actions reruns daily (and on push) and commits a fresh `docs/index.html` if the numbers moved.

## Run locally

```bash
uv sync
uv run python build/render.py
open docs/index.html
```

## Edit the curation overlay

`packages.yml` — override the role line, attach a Zenodo DOI, add a badge, pin a package to the top.

Auto-discovery surfaces any new package not yet in `packages.yml` as a build-log warning; the package still renders (PyPI summary becomes the role text) so new releases never block the site.

## Doctrine

Part of the **subdomain sovereignty** family: every `X.faf.one` is its own thing — own repo, own CF/GH Pages project, own brand. Companions:

- **memory.faf.one** ← `claude-fafm-sdk/docs/` (sibling-product mount)
- **grok.faf.one** ← its own CF Worker
- **pypi.faf.one** ← this repo (dedicated subdomain-serving repo, `<subdomain>-faf` naming)

## License

MIT
