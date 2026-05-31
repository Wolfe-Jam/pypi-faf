<!-- Thanks for the PR. Short is fine. -->

## What

<!-- One or two sentences. -->

## Why

<!-- One sentence on what this clarifies or fixes. -->

## Pre-flight

- [ ] `uv sync && uv run python build/render.py` runs clean locally.
- [ ] If `packages.yml` changed: role lines are ≤ 90 chars and factual (no marketing voice).
- [ ] If `build/render.py` or `templates/index.html.j2` changed: I opened `docs/index.html` in a browser after re-rendering.
- [ ] If a regenerated `docs/index.html` is included in this PR: the data inside matches what's currently on PyPI / pypistats.
