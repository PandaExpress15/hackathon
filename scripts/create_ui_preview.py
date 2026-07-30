#!/usr/bin/env python3
"""Generate a static interface preview from a real bundled-data result."""

from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from careerproof.analysis_engine import analyze_question  # noqa: E402
from careerproof.data_loader import load_bundled_dataset  # noqa: E402
from careerproof.intent_training_data import SUPPORTED_DEMO_QUESTIONS  # noqa: E402


def build_html() -> str:
    bundle = load_bundled_dataset()
    response = analyze_question(SUPPORTED_DEMO_QUESTIONS[1], bundle, write_audit=False)
    rows = response.result.table.head(8)
    max_count = max(int(rows["Postings"].max()), 1)
    bars = "".join(
        f'''<div class="bar-row"><span class="bar-label">{html.escape(str(row['Skill']))}</span><div class="bar-track"><div class="bar" style="width:{int(row['Postings'])/max_count*100:.1f}%"></div></div><b>{int(row['Postings'])}</b></div>'''
        for _, row in rows.iterrows()
    )
    table_rows = "".join(
        f"<tr><td>{html.escape(str(row['Skill']))}</td><td>{int(row['Postings'])}</td><td>{float(row['Share of matched postings']):.1%}</td></tr>"
        for _, row in rows.head(6).iterrows()
    )
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
    *{{box-sizing:border-box}}body{{margin:0;background:#EEF3F6;font-family:Inter,Arial,sans-serif;color:#102A43}}
    .page{{width:1500px;min-height:980px;margin:0 auto;padding:22px 34px}}
    .hero{{height:205px;border-radius:26px;padding:30px 38px;color:white;position:relative;overflow:hidden;background:radial-gradient(circle at 83% 20%,rgba(52,211,153,.28),transparent 25%),linear-gradient(135deg,#0B1F33,#123B53 58%,#0C6A55);box-shadow:0 18px 50px rgba(16,42,67,.22)}}
    .hero:after{{content:"";position:absolute;width:230px;height:230px;border:1px solid rgba(255,255,255,.15);border-radius:50%;right:-55px;top:-90px}}
    .eyebrow{{display:inline-block;border:1px solid rgba(255,255,255,.24);background:rgba(255,255,255,.08);border-radius:999px;padding:6px 10px;font-size:11px;font-weight:800;letter-spacing:.12em;text-transform:uppercase}}
    h1{{font-size:44px;margin:14px 0 5px;letter-spacing:-.035em}}.hero p{{margin:0;color:#D9F3EA;font-size:17px}}
    .badges{{display:flex;gap:8px;margin-top:17px}}.badge{{padding:7px 10px;border:1px solid rgba(255,255,255,.15);background:rgba(255,255,255,.1);border-radius:9px;font-size:12px;font-weight:700}}
    .tabs{{margin:16px 0;display:flex;gap:7px;background:white;border:1px solid #D9E2EC;padding:6px;border-radius:14px}}.tab{{padding:10px 17px;border-radius:10px;color:#627D98;font-weight:700;font-size:13px}}.tab.active{{background:#E9F7F2;color:#0B684D}}
    .dataset{{display:grid;grid-template-columns:2fr repeat(4,1fr);gap:10px;margin-bottom:14px}}.card{{background:white;border:1px solid #D9E2EC;border-radius:16px;box-shadow:0 7px 22px rgba(16,42,67,.05)}}
    .dataset .card{{padding:14px}}.label{{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:#829AB1;font-weight:800}}.value{{font-size:22px;font-weight:850;margin-top:4px}}.sub{{font-size:11px;color:#829AB1;margin-top:2px}}
    .question{{padding:14px 18px;display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}}.question span{{color:#334E68;font-size:16px}}.button{{background:linear-gradient(135deg,#14805E,#0E6A52);color:white;font-weight:800;padding:12px 20px;border-radius:11px}}
    .answer{{padding:18px 22px;border-left:6px solid #14805E;background:linear-gradient(135deg,#fff,#F4FBF8);margin-bottom:12px}}.status{{display:inline-block;background:#DFF4EC;color:#0B684D;padding:5px 9px;border-radius:999px;font-size:10px;font-weight:850;text-transform:uppercase;letter-spacing:.06em}}.answer h2{{font-size:27px;margin:11px 0 5px}}.answer p{{margin:5px 0;color:#627D98;font-size:13px}}.proof{{color:#2F6BFF;font-family:monospace;font-size:12px;margin-top:9px}}
    .proofline{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:12px}}.step{{padding:10px;text-align:center;border:1px solid #9FDAC6;background:#F0FBF7;border-radius:11px;font-size:10px;color:#486581}}.step b{{display:block;color:#102A43;font-size:12px;margin-bottom:2px}}
    .main{{display:grid;grid-template-columns:2.2fr 1fr;gap:12px}}.chart-card{{padding:18px}}.chart-card h3,.side h3{{margin:0 0 14px;font-size:17px}}.bar-row{{display:grid;grid-template-columns:155px 1fr 34px;gap:10px;align-items:center;margin:9px 0}}.bar-label{{font-size:12px;color:#486581}}.bar-track{{height:17px;background:#EAF0F4;border-radius:7px;overflow:hidden}}.bar{{height:100%;background:linear-gradient(90deg,#14805E,#2BB489);border-radius:7px}}.bar-row b{{font-size:11px}}
    .side{{display:grid;grid-template-rows:190px 1fr;gap:12px}}.confidence{{padding:18px;text-align:center}}.ring{{width:112px;height:112px;border-radius:50%;margin:4px auto 10px;background:conic-gradient(#14805E {response.confidence.score}%,#E8EEF4 0);display:grid;place-items:center}}.ring:after{{content:"{response.confidence.score}";width:82px;height:82px;border-radius:50%;background:white;display:grid;place-items:center;font-size:28px;font-weight:850}}.confidence p{{font-size:11px;color:#627D98;margin:4px}}
    .table{{padding:16px}}table{{width:100%;border-collapse:collapse;font-size:11px}}th{{text-align:left;background:#102A43;color:white;padding:8px}}td{{padding:8px;border-bottom:1px solid #E8EEF4}}
    .footer{{margin-top:12px;font-size:10px;color:#829AB1;text-align:right}}
    </style></head><body><div class="page">
      <section class="hero"><div class="eyebrow">Track 2 · Trustworthy Data Analysis</div><h1>CareerProof AI</h1><p>Ask the job market. See the proof. Code-verified answers with visible evidence and privacy protection.</p><div class="badges"><span class="badge">Deterministic calculations</span><span class="badge">Evidence Passport</span><span class="badge">Privacy Shield</span><span class="badge">Safe refusal</span></div></section>
      <div class="tabs"><div class="tab active">Ask the Data</div><div class="tab">Explore</div><div class="tab">Data Quality</div><div class="tab">Trust Center</div><div class="tab">Audit Log</div><div class="tab">About</div></div>
      <div class="dataset"><div class="card"><div class="label">Active dataset</div><div class="value" style="font-size:17px">CareerProof synthetic job postings</div><div class="sub">Fingerprint {bundle.fingerprint} · privacy masking active</div></div><div class="card"><div class="label">Cleaned rows</div><div class="value">{len(bundle.cleaned)}</div><div class="sub">from {len(bundle.raw)} raw</div></div><div class="card"><div class="label">Quality</div><div class="value">{bundle.report.quality_score}/100</div><div class="sub">rule-based</div></div><div class="card"><div class="label">Salary coverage</div><div class="value">{1-bundle.report.missing_salary_percentage:.0%}</div><div class="sub">complete ranges</div></div><div class="card"><div class="label">PII fields</div><div class="value">{len(bundle.report.pii_columns_detected)}</div><div class="sub">masked</div></div></div>
      <div class="card question"><span>{html.escape(response.question)}</span><div class="button">Analyze with proof</div></div>
      <div class="card answer"><span class="status">Verified by code</span><h2>{html.escape(response.result.headline)}</h2><p>{html.escape(response.result.summary)}</p><div class="proof">Evidence ID {response.result.proof_id}</div></div>
      <div class="proofline"><div class="step"><b>1. Question</b>Natural language</div><div class="step"><b>2. Plan</b>Skill frequency</div><div class="step"><b>3. Validate</b>Allowlist passed</div><div class="step"><b>4. Calculate</b>{response.result.rows_used} rows used</div><div class="step"><b>5. Prove</b>{response.result.proof_id[-8:]}</div></div>
      <div class="main"><div class="card chart-card"><h3>Verified ranking from the supplied data</h3>{bars}</div><div class="side"><div class="card confidence"><h3>{response.confidence.label}</h3><div class="ring"></div><p>Based on usable rows, completeness, intent clarity, and dataset quality.</p></div><div class="card table"><h3>Result table</h3><table><thead><tr><th>Skill</th><th>Postings</th><th>Share</th></tr></thead><tbody>{table_rows}</tbody></table></div></div></div>
      <div class="footer">Interface preview generated from the real bundled demo calculation</div>
    </div></body></html>'''


def main() -> None:
    output_dir = ROOT / "docs" / "assets" / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = ROOT / "docs" / "assets" / "ui_preview.html"
    html_path.write_text(build_html(), encoding="utf-8")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(f"Wrote HTML preview to {html_path}. Playwright is not installed, so PNG generation was skipped.")
        return
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path="/usr/bin/chromium",
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(viewport={"width": 1560, "height": 1020}, device_scale_factor=1)
        page.set_content(html_path.read_text(encoding="utf-8"))
        page.screenshot(path=str(output_dir / "dashboard.png"), full_page=False)
        browser.close()
    print(f"Wrote {output_dir / 'dashboard.png'}")


if __name__ == "__main__":
    main()
