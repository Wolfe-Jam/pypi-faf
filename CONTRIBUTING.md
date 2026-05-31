# Contributing to pypi-faf

`pypi-faf` is the discovery showcase for the FAF Python ecosystem at **[pypi.faf.one](https://pypi.faf.one)**. The site is auto-rendered daily from PyPI and pypistats; curation lives in `packages.yml`.

## Three things you can contribute

### 1. Flag a missing package
If a `wolfejam` PyPI package isn't showing up, the auto-discovery scraper (`build/render.py`) didn't pick it up — open a [Missing package](https://github.com/Wolfe-Jam/pypi-faf/issues/new?template=missing-package.yml) issue with the PyPI URL.

### 2. Propose a curation edit
The role line, Zenodo DOI, badge, or pin-order for any package lives in `packages.yml`. Edits:

```yaml
- name: <pypi-package-name>
  role: "<one-line description — keep it short>"
  zenodo: "https://doi.org/<doi>"   # optional, only if the package implements a Zenodo paper
  badge: "<UPPERCASE TAG>"          # optional, sparingly
  pinned: true                      # optional, shows above the download-order sort
```

Open a [Curation edit](https://github.com/Wolfe-Jam/pypi-faf/issues/new?template=curation-edit.yml) issue or send a PR directly. PRs are preferred for one-line role changes.

### 3. Report stale data
The site refreshes once daily via GitHub Actions. If a package shows the wrong version or `0` for downloads on a real package, open a [Stale data](https://github.com/Wolfe-Jam/pypi-faf/issues/new?template=stale-data.yml) issue. Most stale-data reports resolve when the next cron run completes — please check the footer timestamp first.

## Running the renderer locally

```bash
uv sync
uv run python build/render.py
open docs/index.html
```

`render.py` discovers packages from `pypi.org/user/wolfejam/`, hits `pypistats.org` for downloads (without_mirrors only — public-count doctrine), merges the `packages.yml` overlay, and writes `docs/index.html`. The GH Action commits the regenerated HTML if it changed.

## What we will NOT accept

- Packages not authored or co-authored by `wolfejam` (this is a scoped showcase, not a directory).
- Inflated download numbers, "with_mirrors" data, or any pre-counted aggregation.
- Marketing-style role text — keep it factual, technical, under 90 chars.

## Data source transparency

Every number on the page comes from public APIs: PyPI JSON + pypistats.org. The rendered HTML carries the measurement date in the footer. If a measurement looks wrong, the source is auditable — `curl https://pypistats.org/api/packages/<name>/overall`.
