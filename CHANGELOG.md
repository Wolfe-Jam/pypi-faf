# Changelog

All notable changes to `pypi-faf` (the discovery showcase that serves [pypi.faf.one](https://pypi.faf.one)).

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · Versioning: dates of meaningful curation or rendering changes; the rendered HTML auto-refreshes daily.

## [Unreleased]

## [0.1.0] — 2026-05-31

### Added
- Initial scaffold. Auto-discovery of FAF packages from `pypi.org/user/wolfejam/`.
- Curation overlay in `packages.yml` (role, Zenodo DOI, badge, pin).
- Live download numbers from `pypistats.org` (without_mirrors only — public-count doctrine).
- Sovereign landing page at `docs/index.html`; served by GitHub Pages with `pypi.faf.one` custom domain.
- Hero receipts strip: 2 IANA media types + 2 Zenodo papers.
- Daily refresh via GitHub Actions; commit-if-changed on the regenerated HTML.
- Credibility files: `CITATION.cff`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue/PR templates, `dependabot.yml`, `.github/FUNDING.yml`.

### Packages (at first publish)
- claude-fafm-sdk (v0.4.0) — implements .fafm Memory paper · velocity leader
- gemini-faf-mcp (v2.2.5) — implements .faf Context paper
- grok-faf-voice (v0.3.2)
- faf-python-sdk (v1.1.2)
- faf-agent-mcp (v0.1.4)
- slash-tokens (v0.0.2) — placeholder; Python sibling coming soon
