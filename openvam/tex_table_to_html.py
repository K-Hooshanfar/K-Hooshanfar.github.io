"""Convert OpenVAM main_table*.tex files to HTML for the project page."""
from __future__ import annotations

import re
from pathlib import Path

OUT = Path(__file__).resolve().parent / "tables.html"
OPEN_VAM_BG = "#DADCFF"
REF_BG = "#E8E8E8"


def clean_cell(text: str) -> str:
    text = re.sub(r"\\cellcolor\{[^}]+\}", "", text)
    text = re.sub(r"\\cellcolor\[HTML\]\{[^}]+\}", "", text)
    text = re.sub(r"\\textbf\{([^}]*)\}", r"<strong>\1</strong>", text)
    text = re.sub(r"\\textit\{([^}]*)\}", r"<em>\1</em>", text)
    text = re.sub(r"\\scriptsize\{([^}]*)\}", r"<small>\1</small>", text)
    text = re.sub(r"~?\\cite\{[^}]+\}", "", text)
    text = text.replace(r"\%", "%")
    text = text.replace("$", "")
    text = text.replace("~", " ")
    text = text.replace(r"\uparrow", "↑").replace(r"\downarrow", "↓")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_caption(tex: str) -> str:
    m = re.search(r"\\caption\{(.+?)\}\s*\\vspace", tex, re.DOTALL)
    if not m:
        m = re.search(r"\\caption\{(.+?)\}\s*\\label", tex, re.DOTALL)
    if not m:
        return ""
    cap = m.group(1)
    cap = re.sub(r"\\textbf\{([^}]*)\}", r"<strong>\1</strong>", cap)
    return re.sub(r"\s+", " ", cap).strip()


def extract_rows(tex: str) -> list[str]:
    m = re.search(r"\\begin\{tabular\}\{[^}]+\}(.*?)\\end\{tabular\}", tex, re.DOTALL)
    if not m:
        return []
    body = m.group(1)
    body = re.sub(r"\\toprule|\\midrule|\\bottomrule|\\cmidrule\{[^}]+\}", "\n", body)

    rows: list[str] = []
    buf = ""
    for raw in body.split("\n"):
        line = raw.strip()
        if not line or line.startswith("%"):
            continue
        if line.startswith("\\multirow"):
            if buf.strip():
                rows.append(buf.strip())
            rows.append(line)
            buf = ""
            continue
        ends_row = line.rstrip().endswith("\\\\")
        if ends_row:
            line = line[:-2].strip()
        if buf:
            buf += " " + line
        else:
            buf = line
        if ends_row:
            if buf and not any(tok in buf for tok in ("\\toprule", "\\midrule", "\\bottomrule", "\\cmidrule")):
                rows.append(buf)
            buf = ""
    if buf.strip():
        rows.append(buf.strip())
    return rows


def row_class(method: str) -> str:
    if "OpenVAM" in method:
        return "row-openvam"
    if "Gemini" in method:
        return "row-ref"
    return "row-base"


def parse_table1_row(line: str) -> tuple[str, str, str, list[str]] | None:
    """Return (kind, dataset_or_sub, method, metrics) or None."""
    if line.startswith("\\multirow"):
        return None
    if "Dataset" in line and "Method" in line:
        return None
    if line.startswith("(") and "&" not in line:
        return ("sub", "", clean_cell(line), [])

    parts = [clean_cell(p) for p in line.split("&")]
    parts = [p for p in parts]  # keep empty slots for position
    while parts and not parts[0]:
        parts.pop(0)

    if not parts:
        return None

    if parts[0].startswith("(") and len(parts) > 1:
        return ("data", "", parts[0], [parts[1]] + [p for p in parts[2:] if p])

    if parts[0] and ("<em>" in parts[0] or re.search(r"U-EYE|SalECI|OSIE|Salicon|CAT2000|MIT1003", parts[0])):
        dataset = parts[0]
        method = parts[1] if len(parts) > 1 else ""
        metrics = [p for p in parts[2:] if p]
        return ("data", dataset, method, metrics)

    method = parts[0]
    metrics = [p for p in parts[1:] if p]
    return ("data", "", method, metrics)


def build_table1(tex_path: Path) -> str:
    rows = extract_rows(tex_path.read_text(encoding="utf-8"))
    caption = parse_caption(tex_path.read_text(encoding="utf-8"))

    # First pass: collect entries grouped by dataset.
    groups: list[dict] = []
    current_dataset = ""
    current_sub = ""

    for line in rows:
        parsed = parse_table1_row(line)
        if not parsed:
            continue
        kind, dataset, method, metrics = parsed

        if kind == "sub":
            current_sub = method
            continue
        if dataset:
            current_dataset = dataset
            current_sub = ""
            groups.append({"name": dataset, "sub": "", "rows": []})
        elif method.startswith("("):
            current_sub = method
            if metrics:
                method = metrics[0]
                metrics = metrics[1:]
            else:
                continue

        if not method:
            continue
        if not groups:
            groups.append({"name": current_dataset, "sub": "", "rows": []})

        if current_sub and not groups[-1]["sub"]:
            groups[-1]["sub"] = current_sub

        groups[-1]["rows"].append((method, metrics))

    html = [
        '<div class="result-table-wrap" id="table-saliency">',
        f'<p class="table-caption">{caption}</p>',
        '<div class="table-scroll"><table class="result-table">',
        "<colgroup><col class='col-dataset'><col class='col-method'>"
        "<col><col><col><col><col></colgroup>",
        "<thead><tr>",
        "<th>Dataset</th><th>Method</th>",
        "<th>CC&nbsp;↑</th><th>KLD&nbsp;↓</th><th>AUC&nbsp;↑</th><th>SIM&nbsp;↑</th><th>NSS&nbsp;↑</th>",
        "</tr></thead><tbody>",
    ]

    for gi, group in enumerate(groups):
        n = len(group["rows"])
        if not n:
            continue
        sub_html = (
            f"<span class='dataset-sub'>{group['sub']}</span>" if group["sub"] else ""
        )
        sep = " group-start" if gi else ""
        for ri, (method, metrics) in enumerate(group["rows"]):
            cls = row_class(method)
            html.append(f"<tr class='{cls}{sep if ri == 0 else ''}'>")
            if ri == 0:
                html.append(
                    f"<td rowspan='{n}' class='dataset-cell{sep}'>{group['name']}{sub_html}</td>"
                )
            html.append(f"<td class='method-cell'>{method}</td>")
            for m in metrics[:5]:
                html.append(f"<td>{m}</td>")
            for _ in range(max(0, 5 - len(metrics))):
                html.append("<td></td>")
            html.append("</tr>")

    html += ["</tbody></table></div></div>"]
    return "\n".join(html)


def build_table2(tex_path: Path) -> str:
    tex = tex_path.read_text(encoding="utf-8")
    rows = extract_rows(tex)
    caption = parse_caption(tex)

    # First pass: collect groups.
    groups: list[dict] = []
    for line in rows:
        if line.startswith("\\multirow"):
            m = re.search(
                r"\\multirow\{(\d+)\}\{[^}]*\}\{(\\textit\{[^}]+\}(?:~\\cite\{[^}]+\})?)\}",
                line,
            )
            if m:
                groups.append({"name": clean_cell(m.group(2)), "rows": []})
            continue
        if "JScore" in line or ("R-1" in line and "B-1" in line):
            continue

        parts = [clean_cell(p) for p in line.split("&")]
        while parts and not parts[0]:
            parts.pop(0)
        if len(parts) < 2:
            continue

        method = parts[0]
        vals = [p for p in parts[1:] if p]
        if not method or len(vals) < 8:
            continue
        if not groups:
            groups.append({"name": "", "rows": []})
        groups[-1]["rows"].append((method, vals[:8]))

    html = [
        '<div class="result-table-wrap" id="table-vlm">',
        f'<p class="table-caption">{caption}</p>',
        '<div class="table-scroll"><table class="result-table">',
        "<thead>",
        "<tr>",
        "<th rowspan='2'>Dataset</th><th rowspan='2'>Method</th><th rowspan='2'>JScore&nbsp;↑</th>",
        "<th colspan='3'>ROUGE&nbsp;↑</th><th colspan='4'>BLEU&nbsp;↑</th>",
        "</tr>",
        "<tr><th>R-1</th><th>R-2</th><th>R-L</th><th>B-1</th><th>B-2</th><th>B-3</th><th>B-4</th></tr>",
        "</thead><tbody>",
    ]

    for gi, group in enumerate(groups):
        n = len(group["rows"])
        if not n:
            continue
        sep = " group-start" if gi else ""
        for ri, (method, vals) in enumerate(group["rows"]):
            cls = row_class(method)
            html.append(f"<tr class='{cls}{sep if ri == 0 else ''}'>")
            if ri == 0:
                html.append(
                    f"<td rowspan='{n}' class='dataset-cell{sep}'>{group['name']}</td>"
                )
            html.append(f"<td class='method-cell'>{method}</td>")
            for v in vals:
                html.append(f"<td>{v}</td>")
            html.append("</tr>")

    html += ["</tbody></table></div></div>"]
    return "\n".join(html)


def main() -> None:
    root = Path(__file__).resolve().parent
    css = """
<style>
:root {
  --ov-accent: #5b5bd6;
  --ov-accent-soft: #ececfb;
  --ov-head: #2b2d42;
  --ov-border: #e6e6ef;
}
.result-table-wrap { margin: 2.25rem auto 3rem; max-width: 100%; }
.table-caption { margin: 0 auto 1rem; font-size: 0.9rem; line-height: 1.45; color: #3a3a44; max-width: 760px; text-align: center; }
.table-legend { display: flex; gap: 1.25rem; justify-content: center; flex-wrap: wrap; margin: 0 0 0.85rem; font-size: 0.78rem; color: #555; }
.table-legend span { display: inline-flex; align-items: center; gap: 0.4rem; }
.legend-swatch { width: 14px; height: 14px; border-radius: 3px; border: 1px solid rgba(0,0,0,0.08); }
.legend-swatch.ours { background: var(--ov-accent-soft); border-color: var(--ov-accent); }
.legend-swatch.ref { background: #f0f0f3; }
.table-scroll { overflow-x: auto; border: 1px solid var(--ov-border); border-radius: 12px; box-shadow: 0 6px 24px rgba(30,30,60,0.07); -webkit-overflow-scrolling: touch; }
.result-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.76rem; white-space: nowrap; font-variant-numeric: tabular-nums; }
.result-table th, .result-table td { padding: 7px 11px; text-align: center; vertical-align: middle; border-bottom: 1px solid var(--ov-border); }
.result-table thead th { background: var(--ov-head); color: #fff; font-weight: 600; letter-spacing: 0.02em; position: sticky; top: 0; border-bottom: none; }
.result-table thead tr:first-child th { border-bottom: 1px solid rgba(255,255,255,0.18); }
.result-table tbody tr.row-base:nth-of-type(even) { background: #fafafb; }
.result-table tbody tr:hover { background: #f3f3fb; }
.result-table .dataset-cell { font-weight: 700; text-align: left; white-space: normal; min-width: 92px; background: #f6f6fa; border-right: 1px solid var(--ov-border); font-style: italic; color: #2b2d42; }
.result-table .dataset-sub { display: block; font-weight: 400; font-style: normal; font-size: 0.82em; color: #777; margin-top: 2px; }
.result-table .method-cell { text-align: left; font-weight: 500; color: #333; }
.result-table tbody tr.row-openvam { background: var(--ov-accent-soft) !important; }
.result-table tbody tr.row-openvam .method-cell { color: var(--ov-accent); font-weight: 700; }
.result-table tbody tr.row-openvam td { box-shadow: inset 0 0 0 9999px rgba(91,91,214,0.015); }
.result-table tbody tr.row-ref { background: #f0f0f3 !important; }
.result-table tbody tr.row-ref .method-cell { font-style: italic; color: #555; }
.result-table tr.group-start td { border-top: 2px solid #c9c9d6; }
.result-table strong { color: var(--ov-accent); font-weight: 700; }
.result-table small { font-size: 0.8em; color: #8a8a96; font-weight: 400; }
.result-table tbody tr.row-openvam small { color: #7a7ad0; }
</style>
"""
    legend = (
        '<div class="table-legend">'
        '<span><span class="legend-swatch ours"></span>OpenVAM (ours)</span>'
        '<span><strong>bold</strong> = best per metric</span>'
        '</div>'
    )
    t1 = build_table1(root / "main_table1.tex").replace(
        '<div class="table-scroll">', legend + '<div class="table-scroll">', 1
    )
    t2 = build_table2(root / "main_table2.tex").replace(
        '<div class="table-scroll">', legend + '<div class="table-scroll">', 1
    )
    tables = css + t1 + t2
    OUT.write_text(tables, encoding="utf-8")
    print("Wrote", OUT)

    # Inline the tables directly into index.html so the page works without a
    # web server (fetch() is blocked under the file:// protocol).
    index_path = root / "index.html"
    if index_path.exists():
        index = index_path.read_text(encoding="utf-8")
        start = "<!-- TABLES:START -->"
        end = "<!-- TABLES:END -->"
        if start in index and end in index:
            before = index.split(start)[0]
            after = index.split(end)[1]
            index = f"{before}{start}\n{tables}\n      {end}{after}"
            index_path.write_text(index, encoding="utf-8")
            print("Inlined tables into", index_path)


if __name__ == "__main__":
    main()
