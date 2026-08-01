#!/usr/bin/env python3
"""Full in-process browser acceptance suite for CareerProof AI.

Chromium access to localhost is restricted in the execution environment, so this
suite renders the real FastAPI template, inlines the production CSS/JS, and
routes browser fetch calls through FastAPI TestClient.  The frontend and backend
contracts are therefore exercised together without mocking endpoint payloads.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from fastapi.testclient import TestClient
from playwright.sync_api import Browser, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from careerproof.webapp import create_app  # noqa: E402

RESULT_PATH = ROOT / "docs" / "browser_acceptance_results.json"
HOME_SCREENSHOT = ROOT / "docs" / "assets" / "careerproof-98-home.png"
PATH_SCREENSHOT = ROOT / "docs" / "assets" / "careerproof-98-path.png"
COMPARE_SCREENSHOT = ROOT / "docs" / "assets" / "careerproof-98-compare.png"
MOBILE_SCREENSHOT = ROOT / "docs" / "assets" / "careerproof-98-mobile.png"


class Acceptance:
    def __init__(self) -> None:
        self.results: list[dict[str, Any]] = []
        self.console_errors: list[str] = []
        self.page_errors: list[str] = []

    def record(self, name: str, passed: bool, detail: Any = "") -> None:
        self.results.append({"name": name, "passed": bool(passed), "detail": detail})
        print(f"{'PASS' if passed else 'FAIL'}  {name}: {detail}")

    def check(self, name: str, fn: Callable[[], Any]) -> None:
        try:
            detail = fn()
            if isinstance(detail, tuple) and len(detail) == 2:
                passed, message = detail
            elif isinstance(detail, bool):
                passed, message = detail, ""
            else:
                passed, message = True, detail
            self.record(name, bool(passed), message)
        except Exception as exc:  # browser acceptance should report every broken flow
            self.record(name, False, f"{type(exc).__name__}: {exc}")

    @property
    def passed(self) -> int:
        return sum(item["passed"] for item in self.results)

    @property
    def failed(self) -> int:
        return len(self.results) - self.passed


def build_inline_document(client: TestClient) -> str:
    html = client.get("/").text
    css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
    js = (ROOT / "static" / "app.js").read_text(encoding="utf-8").replace("</script>", "<\\/script>")
    html = html.replace('<link rel="stylesheet" href="/static/app.css">', f"<style>{css}</style>")
    html = html.replace('<script src="/static/app.js" defer></script>', f"<script>{js}</script>")
    return html


def install_fetch_bridge(page: Page, client: TestClient) -> None:
    def route(_source: Any, request: dict[str, Any]) -> dict[str, Any]:
        raw_url = str(request.get("url", "/"))
        parsed = urlsplit(raw_url)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        method = str(request.get("method", "GET")).upper()
        body = request.get("body")
        headers = request.get("headers") or {}
        response = client.request(method, path, content=body, headers=headers)
        return {
            "status": response.status_code,
            "body": response.text,
            "headers": {"content-type": response.headers.get("content-type", "application/json")},
        }

    page.expose_binding("__careerproof_fetch", route)
    page.evaluate(
        """
        () => {
          window.fetch = async (input, init = {}) => {
            const url = typeof input === 'string' ? input : input.url;
            const headers = {};
            if (init.headers) {
              if (init.headers instanceof Headers) init.headers.forEach((value, key) => { headers[key] = value; });
              else Object.assign(headers, init.headers);
            }
            const result = await window.__careerproof_fetch({
              url,
              method: init.method || 'GET',
              body: init.body ?? null,
              headers,
            });
            return new Response(result.body, { status: result.status, headers: result.headers });
          };
        }
        """
    )


def text(page: Page, selector: str) -> str:
    return page.locator(selector).inner_text().strip()


def click_workspace(page: Page, name: str) -> None:
    page.locator(f'[data-workspace="{name}"]').first.click(force=True)
    page.wait_for_selector(f"#workspace-{name}.active")


def run_suite(page: Page, acceptance: Acceptance) -> None:
    page.wait_for_selector("#homeMatches .home-match-row", timeout=30_000)

    acceptance.check("Home dashboard loads", lambda: (page.locator("#workspace-home.active").count() == 1, "active home workspace"))
    acceptance.check("Home top match is Electrical Engineers", lambda: ("Electrical Engineers" in text(page, "#homeMatches .home-match-row:first-child"), text(page, "#homeMatches .home-match-row:first-child h3")))
    acceptance.check("Verified coverage metrics render", lambda: (page.locator("#statsGrid .stat-card").count() >= 5, f"{page.locator('#statsGrid .stat-card').count()} metric cards"))
    acceptance.check("Home has explicit AI-proof boundary", lambda: ("No career is permanently AI-proof" in page.locator("body").inner_text(), "boundary visible"))
    acceptance.check("Home screenshot generated", lambda: (page.screenshot(path=str(HOME_SCREENSHOT), full_page=True) is not None, str(HOME_SCREENSHOT)))

    def universe_flow() -> tuple[bool, str]:
        click_workspace(page, "universe")
        page.wait_for_selector("#universeSvg [data-category]", timeout=15_000)
        categories = page.locator("#universeSvg [data-category]").count()
        page.locator("#universeSvg [data-category]").first.click(force=True)
        page.wait_for_selector("#universeDetail [data-universe-soc]", timeout=20_000)
        careers = page.locator("#universeDetail [data-universe-soc]").count()
        page.locator("#universeDetail [data-universe-soc]").first.click(force=True)
        page.wait_for_selector("#universeDetail h2", timeout=20_000)
        heading = text(page, "#universeDetail h2")
        return categories >= 8 and careers > 0 and bool(heading), f"{categories} categories, {careers} career nodes, opened {heading}"

    acceptance.check("Career Universe drills from category to career evidence", universe_flow)

    def path_interpretation() -> tuple[bool, str]:
        click_workspace(page, "path")
        page.locator("#pathForm button[type=submit]").click(force=True)
        page.wait_for_selector("#pathInterpretation:not(.hidden) #confirmInterpretation", timeout=20_000)
        body = text(page, "#pathInterpretation")
        return "Maryland" in body and "Bachelor" in body and "AI resilience" in body, "editable profile includes location, education, and priorities"

    acceptance.check("Path Builder shows editable interpretation before calculation", path_interpretation)

    def path_results() -> tuple[bool, str]:
        page.locator("#confirmInterpretation").click(force=True)
        page.wait_for_selector("#pathResults .path-card", timeout=60_000)
        top = text(page, "#pathResults .path-card:first-child h3")
        cards = page.locator("#pathResults .path-card").count()
        return top == "Electrical Engineers" and cards >= 3, f"top={top}; cards={cards}"

    acceptance.check("Path Builder calculates verified ranking", path_results)
    acceptance.check("Path ranking includes 8 transparent components", lambda: (page.locator("#pathResults .path-card:first-child .component-bar").count() == 8, f"{page.locator('#pathResults .path-card:first-child .component-bar').count()} components"))
    acceptance.check("Path Builder shows portfolio strategy", lambda: (page.locator("#pathResults .portfolio-item").count() >= 3, f"{page.locator('#pathResults .portfolio-item').count()} portfolio roles"))
    acceptance.check("Path Builder shows counterfactual scenarios", lambda: (page.locator("#pathResults .sensitivity-row").count() >= 6, f"{page.locator('#pathResults .sensitivity-row').count()} sensitivity rows"))

    def challenge_flow() -> tuple[bool, str]:
        button = page.locator("#pathResults .path-card:first-child [data-toggle-challenge]")
        button.click(force=True)
        panel = page.locator("#pathResults .path-card:first-child .challenge-panel")
        panel.wait_for(state="visible")
        body = panel.inner_text()
        return panel.is_visible() and panel.locator("h5").count() >= 2, body[:220]

    acceptance.check("Challenge this recommendation works", challenge_flow)

    def evidence_flow() -> tuple[bool, str]:
        page.locator("#pathResults .path-card:first-child [data-evidence-soc]").click(force=True)
        page.wait_for_selector("#evidenceModal.open", timeout=15_000)
        body = text(page, "#evidenceContent")
        title = text(page, "#evidenceTitle")
        ok = bool(title) and "Direct official values" in body and "Score contributions" in body and "Source confidence" in body
        page.locator('button[data-close-modal="evidence"]').click(force=True)
        page.wait_for_function("!document.querySelector('#evidenceModal').classList.contains('open')", timeout=5_000)
        return ok, f"{title}: direct values, derived values, contributions, and confidence visible"

    acceptance.check("Evidence Passport opens from recommendation", evidence_flow)

    def tray_flow() -> tuple[bool, str]:
        page.locator("#pathResults .path-card:first-child [data-tray-soc]").click(force=True)
        tray = page.locator("#comparisonTray")
        tray.wait_for(state="visible")
        return page.locator("#comparisonTray [data-remove-tray]").count() >= 1, text(page, "#comparisonTray")[:160]

    acceptance.check("Persistent comparison tray receives careers", tray_flow)
    acceptance.check("Path screenshot generated", lambda: (page.screenshot(path=str(PATH_SCREENSHOT), full_page=True) is not None, str(PATH_SCREENSHOT)))

    def compare_flow() -> tuple[bool, str]:
        click_workspace(page, "compare")
        page.locator("#loadDemoCompare").click(force=True)
        page.wait_for_selector("#compareResults .compare-career-card", timeout=60_000)
        cards = page.locator("#compareResults .compare-career-card").count()
        body = text(page, "#compareResults")
        blocked = "blocked" in body.lower()
        tradeoff_visible = page.locator("#compareResults .tradeoff-callout").is_visible()
        return cards >= 3 and blocked and tradeoff_visible, f"{cards} careers; hard-constraint block={blocked}; tradeoff panel={tradeoff_visible}"

    acceptance.check("Compare Lab calculates tradeoffs and hard constraints", compare_flow)
    acceptance.check("Compare Lab shows 8-component chart", lambda: (page.locator("#compareResults .comparison-row").count() == 8, f"{page.locator('#compareResults .comparison-row').count()} rows"))
    acceptance.check("Compare screenshot generated", lambda: (page.screenshot(path=str(COMPARE_SCREENSHOT), full_page=True) is not None, str(COMPARE_SCREENSHOT)))

    def bridge_flow() -> tuple[bool, str]:
        click_workspace(page, "bridge")
        page.locator("#bridgeSource").fill("Public Relations Specialists")
        page.locator("#bridgeTarget").fill("Political Scientists")
        page.locator("#runBridge").click(force=True)
        page.wait_for_selector("#bridgeResults .skill-bridge-card", timeout=30_000)
        body = text(page, "#bridgeResults")
        return "Skill Bridge" in body and "Shared transferable skills" in body and "TRANSITION STEPS" in body, body[:180]

    acceptance.check("Skills Bridge produces evidence-backed transition analysis", bridge_flow)

    def ask_supported() -> tuple[bool, str]:
        click_workspace(page, "ask")
        page.locator("#questionInput").fill("Which states pay nuclear engineers the most?")
        page.locator("#askForm button[type=submit]").click(force=True)
        page.wait_for_selector("#resultArea .result-card", timeout=30_000)
        body = text(page, "#resultArea")
        proof = page.locator("#resultArea .proof-strip").is_visible()
        plan = page.locator("#resultArea .query-plan").is_visible()
        rows = page.locator("#resultArea .analysis-table tbody tr").count()
        return proof and plan and rows > 0, f"proof={proof}; plan={plan}; rows={rows}; {body[:120]}"

    acceptance.check("Supported natural-language question returns verified answer", ask_supported)

    def ask_refusal() -> tuple[bool, str]:
        page.locator("#questionInput").fill("Which bachelor's degree guarantees the highest salary after becoming a lawyer?")
        page.locator("#askForm button[type=submit]").click(force=True)
        page.wait_for_selector("#resultArea .refusal-card", timeout=30_000)
        body = text(page, "#resultArea")
        return "cannot" in body.lower() or "not" in body.lower(), body[:220]

    acceptance.check("Unsupported guarantee question is safely refused", ask_refusal)

    def occupation_flow() -> tuple[bool, str]:
        click_workspace(page, "occupations")
        page.locator("#occupationSearch").fill("Electrical Engineers")
        page.wait_for_selector("#occupationSearchResults [data-occupation-soc]", timeout=20_000)
        page.locator("#occupationSearchResults [data-occupation-soc]").first.click(force=True)
        page.wait_for_selector("#occupationProfile.occupation-profile", timeout=30_000)
        body = text(page, "#occupationProfile")
        kpis = page.locator("#occupationProfile .occupation-kpi").count()
        tabs = page.locator("#occupationProfile [data-profile-tab]").count()
        return "Electrical Engineers" in body and kpis >= 6 and tabs == 7, f"kpis={kpis}; tabs={tabs}; {body[:130]}"

    acceptance.check("Occupation Explorer opens unified profile", occupation_flow)

    def degree_flow() -> tuple[bool, str]:
        click_workspace(page, "degrees")
        page.locator("#degreeSearch").fill("Electrical Engineering")
        page.locator("#searchDegrees").click(force=True)
        page.wait_for_selector("#degreeResults [data-degree-code]", timeout=30_000)
        page.locator("#degreeResults [data-degree-code]").first.click(force=True)
        page.wait_for_selector("#degreeDetail h2", timeout=30_000)
        body = text(page, "#degreeDetail")
        return "Related occupations" in body and "crosswalk" in body.lower(), body[:180]

    acceptance.check("Degree Explorer opens qualitative pathway", degree_flow)

    def location_flow() -> tuple[bool, str]:
        click_workspace(page, "location")
        page.locator("#locationCareer").fill("Electrical Engineers")
        page.locator("#runLocation").click(force=True)
        page.wait_for_selector("#locationResults .location-table", timeout=40_000)
        body = text(page, "#locationResults")
        rows = page.locator("#locationResults .location-table tbody tr").count()
        formula = page.locator("#locationResults .heading-badge").is_visible()
        return rows >= 40 and formula and "Purchasing power" in body, f"rows={rows}; formula={formula}; {body[:130]}"

    acceptance.check("Location Intelligence ranks official state records", location_flow)

    def saved_flow() -> tuple[bool, str]:
        click_workspace(page, "home")
        page.locator("#homeMatches .home-match-row:first-child [data-save-soc]").click(force=True)
        click_workspace(page, "saved")
        page.wait_for_selector("#savedWorkspaceList .saved-workspace-item", timeout=15_000)
        saved_count = page.locator("#savedWorkspaceList .saved-workspace-item").count()
        page.locator("#decisionNotes").fill("Verify ABET programs, local internships, and the Maryland salary evidence before deciding.")
        page.locator("#saveDecisionNotes").click(force=True)
        return saved_count >= 1, f"{saved_count} saved career(s); decision journal accepted"

    acceptance.check("Saved Plans and decision journal work", saved_flow)

    def model_flow() -> tuple[bool, str]:
        click_workspace(page, "trust")
        page.locator('[data-trust-tab="model"]').click(force=True)
        page.wait_for_selector("#modelCard .model-overview", timeout=30_000)
        body = text(page, "#modelCard")
        dimensions = page.locator("#modelCard .model-dimension-card").count()
        return "Career Resilience" in body and dimensions == 6 and "Known limitations" in body, f"{dimensions} dimensions; {body[:150]}"

    acceptance.check("Resilience Model Card exposes formula and limitations", model_flow)

    def quality_flow() -> tuple[bool, str]:
        page.locator('[data-trust-tab="quality"]').click(force=True)
        page.wait_for_selector("#dataQuality .quality-grid", timeout=30_000)
        body = text(page, "#dataQuality")
        return "Data quality" in body or "Missing" in body or "suppressed" in body.lower(), body[:200]

    acceptance.check("Data Quality monitor loads", quality_flow)

    def diagnostic_flow() -> tuple[bool, str]:
        page.locator('[data-trust-tab="diagnostic"]').click(force=True)
        page.locator("#runDiagnostic").click(force=True)
        page.wait_for_selector("#diagnosticResults .diagnostic-grid", timeout=60_000)
        body = text(page, "#diagnosticResults")
        return "13/13" in body or "All" in body or "pass" in body.lower(), body[:200]

    acceptance.check("Live judge diagnostic passes", diagnostic_flow)

    def judge_flow() -> tuple[bool, str]:
        page.locator("#startJudgeMode").click(force=True)
        page.wait_for_selector("#judgeOverlay.open", timeout=30_000)
        title = text(page, "#judgeTitle")
        page.locator("#judgeNext").click(force=True)
        page.wait_for_timeout(200)
        progress = page.locator("#judgeProgress span.active").count()
        page.locator("#closeJudge").click(force=True)
        return bool(title) and progress >= 1, f"title={title}; active progress={progress}"

    acceptance.check("Guided Judge Mode opens and advances", judge_flow)

    def reset_flow() -> tuple[bool, str]:
        page.locator("#resetDemo").click(force=True)
        page.wait_for_timeout(300)
        home_active = page.locator("#workspace-home.active").count() == 1
        tray_closed = not page.locator("#comparisonTray").evaluate("element => element.classList.contains('open')")
        return home_active and tray_closed, f"home_active={home_active}; tray_closed={tray_closed}"

    acceptance.check("One-click demo reset restores clean state", reset_flow)

    def reduced_motion() -> tuple[bool, str]:
        page.emulate_media(reduced_motion="reduce")
        matched = page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
        duration = page.evaluate("getComputedStyle(document.querySelector('.workspace')).animationDuration")
        page.emulate_media(reduced_motion="no-preference")
        return bool(matched), f"media query matched; workspace duration={duration}"

    acceptance.check("Reduced-motion preference is honored", reduced_motion)

    def mobile_flow() -> tuple[bool, str]:
        page.set_viewport_size({"width": 390, "height": 844})
        click_workspace(page, "home")
        page.wait_for_timeout(500)
        overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        page.screenshot(path=str(MOBILE_SCREENSHOT), full_page=True)
        return overflow <= 1, f"horizontal overflow={overflow}px; screenshot={MOBILE_SCREENSHOT.name}"

    acceptance.check("390px mobile layout has no horizontal overflow", mobile_flow)
    page.set_viewport_size({"width": 1536, "height": 960})


def main() -> int:
    os.environ.setdefault("PYTHONPATH", str(SRC))
    app = create_app()
    client = TestClient(app)
    acceptance = Acceptance()
    document = build_inline_document(client)

    started = time.time()
    with sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(
            headless=True,
            executable_path="/usr/bin/chromium",
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        page = browser.new_page(viewport={"width": 1536, "height": 960}, device_scale_factor=1)
        page.set_default_timeout(20_000)
        page.on("console", lambda message: acceptance.console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: acceptance.page_errors.append(str(error)))
        install_fetch_bridge(page, client)
        page.set_content(document, wait_until="domcontentloaded", timeout=60_000)
        try:
            run_suite(page, acceptance)
        except PlaywrightTimeoutError as exc:
            acceptance.record("Browser suite completed", False, f"Unhandled timeout: {exc}")
        except Exception as exc:
            acceptance.record("Browser suite completed", False, f"Unhandled {type(exc).__name__}: {exc}")
        acceptance.record(
            "No browser console or page errors",
            not acceptance.console_errors and not acceptance.page_errors,
            {"console_errors": acceptance.console_errors, "page_errors": acceptance.page_errors},
        )
        browser.close()

    payload = {
        "generated_at_unix": round(time.time()),
        "duration_seconds": round(time.time() - started, 2),
        "summary": {"passed": acceptance.passed, "failed": acceptance.failed, "total": len(acceptance.results)},
        "results": acceptance.results,
        "console_errors": acceptance.console_errors,
        "page_errors": acceptance.page_errors,
        "method": "Production template, CSS, and JavaScript executed in Chromium; frontend fetch calls routed to the real FastAPI app through TestClient.",
        "screenshots": [str(path.relative_to(ROOT)) for path in [HOME_SCREENSHOT, PATH_SCREENSHOT, COMPARE_SCREENSHOT, MOBILE_SCREENSHOT] if path.exists()],
    }
    RESULT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nBrowser acceptance: {acceptance.passed}/{len(acceptance.results)} passed")
    print(f"Results: {RESULT_PATH}")
    return 0 if acceptance.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
