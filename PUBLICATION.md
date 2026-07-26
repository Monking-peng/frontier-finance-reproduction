# Public snapshot policy

This repository is a public, allowlisted snapshot of the independent
FrontierFinance reproduction workspace.

- Current source workspace commit: `f29a9c6e7eaa3833e97f89f99064e841e8350330`
- Initial allowlisted snapshot commit: `8230bf1ae4b894a2be20d31fe45e8f633646aaa9`
- Demo code commit: `76612b92cef57507f1af7ca6854623dc7ce278b5`
- Publication date: `2026-07-26`
- Visibility: public

The snapshot includes source code, tests, configurations, derived results,
sanitized run manifests, public benchmark excerpts, research notes, and the
GitHub Pages site. It excludes local caches, credentials, original SEC filing
bytes, downloaded upstream repositories, virtual environments, and the private
development Git history.

Absolute local executable paths in `command.txt` and `run_manifest.json` were
replaced with the equivalent portable `ffrepro` command. Hash records for every
changed, shipped artifact were recomputed. SEC source bytes remain excluded;
their URLs, filing dates, sizes, and original SHA-256 values are preserved in
the source manifests.

Publication validation: 8/8 project tests, Ruff, JavaScript syntax, JSON parsing,
and shipped-artifact hash checks passed. The first local `uv sync --frozen`
attempt could not discover the workspace's unregistered Python 3.13.14 runtime;
the same version was then supplied explicitly and the full validation passed.
