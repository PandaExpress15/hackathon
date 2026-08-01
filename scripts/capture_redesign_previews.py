#!/usr/bin/env python3
"""Capture presentation-ready screenshots of the actual CareerProof 5.0 UI."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT / "scripts"))

from careerproof.webapp import create_app  # noqa: E402
from browser_acceptance import build_inline_document, install_fetch_bridge  # noqa: E402

OUT = ROOT / "docs" / "redesign-previews"
OUT.mkdir(parents=True, exist_ok=True)


def shot(page, name: str, selector: str | None = None) -> None:
    if selector:
        page.locator(selector).first.scroll_into_view_if_needed()
    page.evaluate("window.scrollTo(0, 0); document.documentElement.scrollTop = 0; document.body.scrollTop = 0; document.activeElement && document.activeElement.blur(); document.querySelectorAll('.autocomplete-menu').forEach((menu) => menu.classList.remove('open'))")
    page.wait_for_timeout(500)
    page.screenshot(path=str(OUT / name), full_page=False)
    print(f"captured {name}")


def workspace(page, name: str) -> None:
    page.evaluate(f"switchWorkspace('{name}', {{scroll: false}})")
    page.wait_for_selector(f"#workspace-{name}.active")
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(200)


def main() -> int:
    client = TestClient(create_app())
    document = build_inline_document(client)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path="/usr/bin/chromium",
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        page = browser.new_page(viewport={"width": 1536, "height": 960}, device_scale_factor=1)
        page.set_default_timeout(40_000)
        install_fetch_bridge(page, client)
        page.set_content(document, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_selector("#homeMatches .home-match-row", timeout=40_000)
        page.add_style_tag(content="*{scroll-behavior:auto!important}.workspace{animation:none!important}")

        shot(page, "01-home.png")

        workspace(page, "universe")
        page.wait_for_selector("#universeSvg [data-category]")
        shot(page, "02-career-universe-overview.png")
        if page.locator(".universe-hotspot").count():
            page.locator(".universe-hotspot").first.click(force=True)
        else:
            page.locator("#universeSvg [data-category]").first.click(force=True)
        page.wait_for_selector("#universeDetail [data-universe-soc]")
        shot(page, "03-career-universe-field.png")
        if page.locator(".reference-moon").count():
            page.locator(".reference-moon").first.click(force=True)
        else:
            page.locator("#universeDetail [data-universe-soc]").first.click(force=True)
        page.wait_for_selector("#universeDetail h2", timeout=40_000)
        shot(page, "03b-career-universe-profile.png")

        workspace(page, "path")
        page.locator("#pathForm button[type=submit]").click(force=True)
        page.wait_for_selector("#confirmInterpretation")
        page.locator("#confirmInterpretation").click(force=True)
        page.wait_for_selector("#pathResults .path-card", timeout=80_000)
        shot(page, "04-build-my-path.png")

        workspace(page, "compare")
        page.locator("#loadDemoCompare").click(force=True)
        page.wait_for_selector("#compareResults .compare-career-card", timeout=80_000)
        page.locator("#toggleCompareSetup").click(force=True)
        shot(page, "05-compare-lab.png")

        workspace(page, "bridge")
        page.evaluate("""
          const source = document.querySelector('#bridgeSource');
          const target = document.querySelector('#bridgeTarget');
          source.value = 'Electrical and Electronic Engineering Technologists and Technicians';
          source.dataset.soc = '17-3023';
          target.value = 'Electrical Engineers';
          target.dataset.soc = '17-2071';
        """)
        page.locator("#runBridge").click(force=True)
        page.wait_for_selector("#bridgeResults .skill-bridge-card", timeout=60_000)
        shot(page, "06-skills-bridge.png")

        workspace(page, "trust")
        page.wait_for_selector("#sourceCatalog .source-card")
        shot(page, "07-evidence-center.png")

        workspace(page, "ask")
        page.locator("#questionInput").fill("Which states pay nuclear engineers the most?")
        page.locator("#askForm button[type=submit]").click(force=True)
        page.wait_for_selector("#resultArea .result-card", timeout=60_000)
        shot(page, "08-ask-careerproof.png")

        workspace(page, "occupations")
        page.locator("#occupationSearch").fill("Electrical Engineers")
        page.wait_for_selector("#occupationSearchResults [data-occupation-soc]")
        page.locator("#occupationSearchResults [data-occupation-soc]").first.click(force=True)
        page.wait_for_selector("#occupationProfile.occupation-profile", timeout=60_000)
        shot(page, "09-occupation-explorer.png")

        workspace(page, "degrees")
        page.locator("#degreeSearch").fill("Electrical Engineering")
        page.locator("#searchDegrees").click(force=True)
        page.wait_for_selector("#degreeResults [data-degree-code]", timeout=60_000)
        page.locator("#degreeResults [data-degree-code]").first.click(force=True)
        page.wait_for_selector("#degreeDetail h2", timeout=60_000)
        shot(page, "10-degree-explorer.png")

        workspace(page, "location")
        page.evaluate("""
          const input = document.querySelector('#locationCareer');
          input.value = 'Electrical Engineers';
          input.dataset.soc = '17-2071';
        """)
        page.locator("#runLocation").click(force=True)
        page.wait_for_selector("#locationResults .location-table", timeout=80_000)
        shot(page, "11-location-intelligence.png")

        # Save the top Path Builder result and show the resulting action plan.
        page.evaluate("switchWorkspace('path', {scroll: false})")
        page.locator("#pathResults .path-card:first-child [data-save-soc]").click(force=True)
        workspace(page, "saved")
        page.wait_for_timeout(300)
        shot(page, "12-my-career-plan.png")

        page.locator("#startJudgeMode").click(force=True)
        page.wait_for_selector("#judgeOverlay.open #judgeTimeline .judge-timeline-step", timeout=30_000)
        shot(page, "13-judge-mode.png", "#judgeOverlay")

        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
