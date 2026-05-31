# Security Policy

## Reporting a vulnerability

For security issues in `pypi-faf` (the renderer, the GH Action, or the published site), please **do not open a public issue**.

**Use GitHub's private vulnerability reporting:** [Open a security advisory](https://github.com/Wolfe-Jam/pypi-faf/security/advisories/new).

Expect an initial reply within a few business days.

## Scope

This repo serves `pypi.faf.one` — a single static page generated from public PyPI + pypistats data. There is no user input, no auth, no server-side execution at runtime. The realistic surface is:

- `build/render.py` — parses upstream JSON and renders HTML. A malicious upstream response could in principle inject content; the renderer escapes HTML via Jinja autoescape.
- The GH Action workflow — has `contents: write` to commit the regenerated `docs/index.html`.
- `docs/` — served by GitHub Pages.

For vulnerabilities in the **packages this showcase references** (claude-fafm-sdk, gemini-faf-mcp, faf-python-sdk, etc.), please report directly to each package's repository.

## Out of scope

- Stale download numbers (data lag; not a security issue — see [CONTRIBUTING.md](./CONTRIBUTING.md)).
- Missing or new PyPI packages not yet picked up (next cron will surface them).
