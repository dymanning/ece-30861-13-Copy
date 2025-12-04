# Accessibility checks (WCAG) — project guide

This project includes an automated accessibility scorer that uses axe-core
(via `axe-selenium-python`) to detect WCAG-related issues and compute a
simple numeric score for pages.

Files added

- `phase2/flask_app/tools/accessibility_scorer.py` — runner that uses Selenium
  + Scans multiple pages, computes per-page penalty and score, writes
  `accessibility-report.json`.
- `.github/workflows/accessibility.yml` — workflow that runs the scorer on push
  and pull requests to `main` and `devDylan` and uploads the report as an artifact.

How scoring works (summary)

- Axe reports violations with `tags` (often include `wcag2a`, `wcag2aa`, etc.)
  and an `impact` (`critical`, `serious`, `moderate`, `minor`).
- The scorer maps WCAG-level tags to a `level_weight` and maps `impact` to
  an `impact_multiplier`.
- Each violation's penalty = `BASE_PENALTY * impact_multiplier * level_weight * nodes`.
  The `nodes` count increases penalty proportionally to how many elements the
  violation affects.
- The page score is `max(0, 100 - total_penalty)` (tunable). The default
  threshold used by the workflow is `90`.
- The scorer fails (exits non-zero) if any scanned page's score is below the
  threshold or when `AXE_FAIL_ON_CRITICAL=true` and any critical violations are found.

Configuring which pages to scan

- Locally or in CI you can set the `PAGES` environment variable to a
  comma-separated list of paths to scan. Example:

```
PAGES='/,/login,/register,/dashboard,/admin'
```

- The `TARGET_URL` environment variable sets the base host (default
  `http://127.0.0.1:3000`). The workflow sets this automatically.

Running locally

1. Install dependencies (in `phase2/flask_app`):

```bash
python3 -m venv .venv
source .venv/bin/activate
./.venv/bin/python -m pip install -r phase2/flask_app/requirements.txt
```

2. Start the Flask app (set `FLASK_SECRET` and any other env vars required):

```bash
export FLASK_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
export JWT_API_URL=http://localhost:5001  # if needed
./.venv/bin/python phase2/flask_app/app.py
```

3. Run the scorer against the pages:

```bash
PAGES='/,/login,/register' TARGET_URL='http://127.0.0.1:3000' \
  python phase2/flask_app/tools/accessibility_scorer.py
```

Interpreting results

- After a run, `accessibility-report.json` is written. It contains per-page
  scores, the violations detected, `total_penalty`, and `critical_violations`.
- The workflow uploads the report as an artifact on every run.

Tuning and policy

- You can adjust the weight tables in `accessibility_scorer.py` (`LEVEL_WEIGHTS`,
  `IMPACT_MULT`, and `BASE_PENALTY`) to make the scorer stricter or more lenient.
- Recommended policy options:
  - Fail fast on any `critical` violation (default configured in the workflow).
  - Allow non-critical violations but enforce a minimum page score (e.g., 90).

CI considerations

- Axe scans can be slow. Limit the number of pages in CI to the critical
  surfaces, and run a more extensive scan nightly if needed.
- The workflow installs Chrome; ensure your CI runner supports installing
  and running headless Chrome. The current workflow uses `google-chrome-stable`.

Notes and limitations

- Automated tools find many issues but do not replace manual accessibility
  testing, screen reader testing, and keyboard navigation checks.
- For dynamic single-page apps you may need to interact with the UI (open
  menus, navigate) before calling the scanner. The scorer supports using
  Selenium so adding interaction steps is straightforward.

Questions or changes

If you'd like, I can:
- Add a `pytest` wrapper that fails the test suite when scores fall below the
  threshold.
- Add nightly workflow for full-site scans and a shorter CI workflow for PRs.
- Adjust scoring weights to match your project's accessibility policy.

