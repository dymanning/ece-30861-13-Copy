import os
import json
import math
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from axe_selenium_python import Axe

# Scoring configuration
LEVEL_WEIGHTS = {
    "wcag2a": 1,
    "wcag21a": 1,
    "wcag2aa": 2,
    "wcag21aa": 2,
    "wcag2aaa": 3,
    "wcag21aaa": 3,
}
IMPACT_MULT = {"critical": 5, "serious": 3, "moderate": 2, "minor": 1}
BASE_PENALTY = 1


def compute_penalty(violation):
    tags = violation.get("tags", [])
    level_weight = 1
    for t in tags:
        if t in LEVEL_WEIGHTS and LEVEL_WEIGHTS[t] > level_weight:
            level_weight = LEVEL_WEIGHTS[t]
    impact = violation.get("impact") or "moderate"
    impact_score = IMPACT_MULT.get(impact, 2)
    nodes = len(violation.get("nodes", []))
    penalty = BASE_PENALTY * impact_score * level_weight * max(1, nodes)
    return penalty


def score_url(url, headless=True, timeout=5):
    opts = Options()
    if headless:
        # use the newer headless mode if available
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    try:
        driver.set_page_load_timeout(timeout)
        driver.get(url)
        time.sleep(0.5)
        axe = Axe(driver)
        axe.inject()
        results = axe.run()
        violations = results.get("violations", [])
        total_penalty = sum(compute_penalty(v) for v in violations)
        # Normalize: simple approach, tune as needed
        score = max(0, 100 - total_penalty)
        return {
            "url": url,
            "score": score,
            "total_penalty": total_penalty,
            "violations_count": len(violations),
            "violations": violations,
            "raw": results,
        }
    finally:
        driver.quit()


if __name__ == "__main__":
    import sys

    # Base target URL (default to local dev server)
    base = os.environ.get("TARGET_URL", "http://127.0.0.1:3000").rstrip("/")
    # PAGES env var: comma-separated paths to scan (e.g. "/,/login,/register")
    pages_env = os.environ.get("PAGES")
    if pages_env:
        pages = [p.strip() for p in pages_env.split(",") if p.strip()]
    else:
        # default pages to scan
        pages = ["/", "/login", "/register", "/dashboard", "/admin"]

    threshold = float(os.environ.get("AXE_SCORE_THRESHOLD", "90"))
    fail_on_critical = os.environ.get("AXE_FAIL_ON_CRITICAL", "true").lower() in ("1", "true", "yes")

    reports = []
    overall_fail = False
    for p in pages:
        url = p if p.startswith("http") else f"{base}{p if p.startswith('/') else '/' + p}"
        print(f"Scanning {url} ...")
        try:
            out = score_url(url, headless=True)
        except Exception as e:
            print(f"Error scanning {url}: {e}")
            reports.append({"url": url, "error": str(e)})
            overall_fail = True
            continue

        critical_violations = [v for v in out.get("violations", []) if v.get("impact") == "critical"]
        report = {
            "url": out["url"],
            "score": out["score"],
            "total_penalty": out["total_penalty"],
            "violations_count": out["violations_count"],
            "critical_violations": len(critical_violations),
            "violations": out.get("violations", []),
        }
        reports.append(report)

        if out["score"] < threshold:
            print(f"Score {out['score']} for {url} is below threshold {threshold}")
            overall_fail = True
        if fail_on_critical and len(critical_violations) > 0:
            print(f"Found {len(critical_violations)} critical violation(s) on {url}")
            overall_fail = True

    # write combined artifact
    combined = {
        "base": base,
        "pages": pages,
        "reports": reports,
    }
    with open("accessibility-report.json", "w") as fh:
        json.dump(combined, fh, indent=2)

    print(json.dumps({"summary": [{"url": r.get("url"), "score": r.get("score"), "critical_violations": r.get("critical_violations")} for r in reports]}, indent=2))

    if overall_fail:
        print("Accessibility checks failed (see accessibility-report.json)")
        sys.exit(2)

    print("Accessibility checks passed")
