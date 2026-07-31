from __future__ import annotations

from html import escape
from typing import Any


def render_html_report(result: dict[str, Any]) -> str:
    rows = result.get("rows", [])
    columns = result.get("columns", [])
    header = "".join(f"<th>{escape(str(column.get('label', column.get('key', ''))))}</th>" for column in columns)
    body_parts = []
    for row in rows:
        cells = "".join(f"<td>{escape(str(row.get(column.get('key'), '')))}</td>" for column in columns)
        body_parts.append(f"<tr>{cells}</tr>")
    sources = "".join(
        f"<li><a href=\"{escape(source.get('url', ''))}\">{escape(source.get('agency', ''))}: {escape(source.get('title', ''))} ({escape(source.get('vintage', ''))})</a></li>"
        for source in result.get("sources", [])
    )
    limitations = "".join(f"<li>{escape(str(item))}</li>" for item in result.get("limitations", []))
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><title>CareerProof Evidence Report</title>
<style>body{{font-family:Arial,sans-serif;max-width:1000px;margin:40px auto;color:#10233d;line-height:1.5}}h1{{color:#0b2948}}.badge{{display:inline-block;padding:6px 10px;border-radius:999px;background:#e9f8f2;color:#087a55;font-weight:700}}table{{border-collapse:collapse;width:100%;margin:24px 0}}th,td{{border-bottom:1px solid #d9e2ec;padding:10px;text-align:left}}th{{background:#eff6ff}}code,pre{{background:#f5f7fa;padding:12px;border-radius:8px;display:block;white-space:pre-wrap}}a{{color:#2563eb}}</style></head>
<body><div class=\"badge\">Verified by code · {escape(result.get('evidence_id', ''))}</div><h1>{escape(result.get('headline', 'CareerProof result'))}</h1>
<p><strong>Question:</strong> {escape(result.get('question', ''))}</p><p>{escape(result.get('summary', ''))}</p>
<h2>Evidence table</h2><table><thead><tr>{header}</tr></thead><tbody>{''.join(body_parts)}</tbody></table>
<h2>Calculation</h2><p>{escape(str(result.get('evidence', {}).get('calculation', '')))}</p><pre>{escape(str(result.get('query_plan', {})))}</pre>
<h2>Sources</h2><ul>{sources}</ul><h2>Limitations</h2><ul>{limitations}</ul>
<p><small>CareerProof AI uses official published data. AI classifies the question; deterministic code calculates displayed facts.</small></p></body></html>"""
