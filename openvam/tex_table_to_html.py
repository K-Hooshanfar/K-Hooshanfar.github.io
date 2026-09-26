"""Convert OpenVAM main_table*.tex files to HTML for the project page."""

from __future__ import annotations

import re
from pathlib import Path


OUT = Path(__file__).resolve().parent / "tables.html"


# ================================================================
# LaTeX helpers
# ================================================================


def unwrap_latex_macro(text: str, macro: str) -> str:
    """
    Remove a LaTeX wrapper while preserving its contents.

    Handles nested braces correctly.

    Examples:
        \\ourscell{OpenVAM-3B}
            -> OpenVAM-3B

        \\ourscell{\\textbf{OpenVAM-3B}}
            -> \\textbf{OpenVAM-3B}
    """

    token = "\\" + macro + "{"

    while token in text:
        start = text.find(token)

        if start == -1:
            break

        content_start = start + len(token)

        depth = 1
        i = content_start

        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1

            elif text[i] == "}":
                depth -= 1

            i += 1

        if depth != 0:
            # Malformed LaTeX: leave it alone.
            break

        content = text[content_start : i - 1]

        text = (
            text[:start]
            + content
            + text[i:]
        )

    return text


def replace_latex_macro(
    text: str,
    macro: str,
    before: str,
    after: str,
) -> str:
    """
    Convert a balanced-brace LaTeX macro to HTML.

    Example:

        \\textbf{hello}
            -> <strong>hello</strong>
    """

    token = "\\" + macro + "{"

    while token in text:
        start = text.find(token)

        if start == -1:
            break

        content_start = start + len(token)

        depth = 1
        i = content_start

        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1

            elif text[i] == "}":
                depth -= 1

            i += 1

        if depth != 0:
            break

        content = text[content_start : i - 1]

        # Process nested occurrences too.
        content = replace_latex_macro(
            content,
            macro,
            before,
            after,
        )

        text = (
            text[:start]
            + before
            + content
            + after
            + text[i:]
        )

    return text


def clean_cell(text: str) -> str:
    """Convert LaTeX used inside table cells to HTML."""

    text = text.strip()

    # Remove trailing LaTeX row marker.
    text = re.sub(
        r"\\\\\s*$",
        "",
        text,
    ).strip()

    # Cell / row colors.
    text = re.sub(
        r"\\cellcolor(?:\[HTML\])?\{[^}]+\}",
        "",
        text,
    )

    text = re.sub(
        r"\\rowcolor(?:\[HTML\])?\{[^}]+\}",
        "",
        text,
    )

    # ------------------------------------------------------------
    # Custom macros
    # ------------------------------------------------------------

    # These wrappers should not appear in the final HTML.
    #
    # This handles:
    #
    # \ourscell{OpenVAM-3B}
    #
    # AND:
    #
    # \ourscell{\textbf{OpenVAM-3B}}
    #
    text = unwrap_latex_macro(
        text,
        "ourscell",
    )

    # Convert best-value macro to bold.
    text = replace_latex_macro(
        text,
        "bestvlm",
        "<strong>",
        "</strong>",
    )

    # ------------------------------------------------------------
    # Standard formatting
    # ------------------------------------------------------------

    text = replace_latex_macro(
        text,
        "textbf",
        "<strong>",
        "</strong>",
    )

    text = replace_latex_macro(
        text,
        "textit",
        "<em>",
        "</em>",
    )

    text = replace_latex_macro(
        text,
        "scriptsize",
        "<small>",
        "</small>",
    )

    # Some source files might nest \ourscell around another macro.
    # Run it one more time after formatting.
    text = unwrap_latex_macro(
        text,
        "ourscell",
    )

    # Remove citations.
    text = re.sub(
        r"~?\\cite\{[^}]+\}",
        "",
        text,
    )

    text = text.replace(
        r"\%",
        "%",
    )

    text = text.replace(
        "$",
        "",
    )

    text = text.replace(
        "~",
        " ",
    )

    text = text.replace(
        r"\uparrow",
        "↑",
    )

    text = text.replace(
        r"\downarrow",
        "↓",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def parse_caption(tex: str) -> str:

    m = re.search(
        r"\\caption\{(.+?)\}\s*\\vspace",
        tex,
        re.DOTALL,
    )

    if not m:
        m = re.search(
            r"\\caption\{(.+?)\}\s*\\label",
            tex,
            re.DOTALL,
        )

    if not m:
        return ""

    cap = m.group(1)

    cap = replace_latex_macro(
        cap,
        "textbf",
        "<strong>",
        "</strong>",
    )

    cap = re.sub(
        r"~?\\cite\{[^}]+\}",
        "",
        cap,
    )

    return re.sub(
        r"\s+",
        " ",
        cap,
    ).strip()


def extract_rows(tex: str) -> list[str]:

    m = re.search(
        r"\\begin\{tabular\}\{[^}]+\}(.*?)\\end\{tabular\}",
        tex,
        re.DOTALL,
    )

    if not m:
        return []

    body = m.group(1)

    body = re.sub(
        r"\\toprule",
        "\n",
        body,
    )

    body = re.sub(
        r"\\midrule",
        "\n",
        body,
    )

    body = re.sub(
        r"\\bottomrule",
        "\n",
        body,
    )

    body = re.sub(
        r"\\cmidrule(?:\([^)]*\))?\{[^}]+\}",
        "\n",
        body,
    )

    rows: list[str] = []
    buffer = ""

    for raw in body.splitlines():

        line = raw.strip()

        if not line:
            continue

        if line.startswith("%"):
            continue

        if line.startswith(r"\addlinespace"):
            continue

        ends_row = line.endswith(r"\\")

        if ends_row:
            line = line[:-2].strip()

        if buffer:
            buffer += " " + line
        else:
            buffer = line

        if ends_row:

            if buffer.strip():
                rows.append(
                    buffer.strip()
                )

            buffer = ""

    if buffer.strip():
        rows.append(
            buffer.strip()
        )

    return rows


def row_class(method: str) -> str:

    plain = re.sub(
        r"<[^>]+>",
        "",
        method,
    )

    if "OpenVAM" in plain:
        return "row-openvam"

    if "Gemini" in plain:
        return "row-ref"

    return "row-base"


def unwrap_multirow(text: str) -> str | None:

    text = text.strip()

    if not text.startswith(r"\multirow"):
        return None

    # Find third {...} argument.
    pos = len(r"\multirow")

    arguments = []

    while len(arguments) < 3:

        # Skip optional [..]
        while pos < len(text) and text[pos].isspace():
            pos += 1

        if pos < len(text) and text[pos] == "[":
            end = text.find("]", pos)

            if end == -1:
                return None

            pos = end + 1

            while pos < len(text) and text[pos].isspace():
                pos += 1

        if pos >= len(text) or text[pos] != "{":
            return None

        depth = 1
        start = pos + 1
        pos += 1

        while pos < len(text) and depth:

            if text[pos] == "{":
                depth += 1

            elif text[pos] == "}":
                depth -= 1

            pos += 1

        if depth != 0:
            return None

        arguments.append(
            text[start : pos - 1]
        )

    return arguments[2]


# ================================================================
# TABLE 1
# ================================================================


def parse_table1_row(
    line: str,
) -> tuple[str, str, str, list[str]] | None:

    if "Dataset" in line and "Method" in line:
        return None

    parts = [
        clean_cell(p)
        for p in line.split("&")
    ]

    while parts and not parts[0]:
        parts.pop(0)

    if not parts:
        return None

    if parts[0].startswith("(") and len(parts) > 1:

        return (
            "data",
            "",
            parts[0],
            [parts[1]]
            + [
                p
                for p in parts[2:]
                if p
            ],
        )

    if parts[0] and (
        "<em>" in parts[0]
        or re.search(
            r"U-EYE|SalECI|OSIE|Salicon|CAT2000|MIT1003",
            parts[0],
        )
    ):

        dataset = parts[0]

        method = (
            parts[1]
            if len(parts) > 1
            else ""
        )

        metrics = [
            p
            for p in parts[2:]
            if p
        ]

        return (
            "data",
            dataset,
            method,
            metrics,
        )

    method = parts[0]

    metrics = [
        p
        for p in parts[1:]
        if p
    ]

    return (
        "data",
        "",
        method,
        metrics,
    )


def build_table1(tex_path: Path) -> str:

    tex = tex_path.read_text(
        encoding="utf-8",
    )

    rows = extract_rows(tex)
    caption = parse_caption(tex)

    groups: list[dict] = []

    current_dataset = ""

    for line in rows:

        parsed = parse_table1_row(
            line
        )

        if not parsed:
            continue

        _, dataset, method, metrics = parsed

        if dataset:

            current_dataset = dataset

            groups.append(
                {
                    "name": dataset,
                    "rows": [],
                }
            )

        if not groups:

            groups.append(
                {
                    "name": current_dataset,
                    "rows": [],
                }
            )

        if method:

            groups[-1]["rows"].append(
                (
                    method,
                    metrics,
                )
            )

    html = [
        '<div class="result-table-wrap" id="table-saliency">',
        f'<p class="table-caption">{caption}</p>',
        '<div class="table-scroll">',
        '<table class="result-table">',
        "<thead>",
        "<tr>",
        "<th>Dataset</th>",
        "<th>Method</th>",
        "<th>CC ↑</th>",
        "<th>KLD ↓</th>",
        "<th>AUC ↑</th>",
        "<th>SIM ↑</th>",
        "<th>NSS ↑</th>",
        "</tr>",
        "</thead>",
        "<tbody>",
    ]

    for group in groups:

        n = len(
            group["rows"]
        )

        if not n:
            continue

        for ri, (
            method,
            metrics,
        ) in enumerate(group["rows"]):

            cls = row_class(
                method
            )

            html.append(
                f'<tr class="{cls}">'
            )

            if ri == 0:

                html.append(
                    f'<td rowspan="{n}" '
                    f'class="dataset-cell">'
                    f'{group["name"]}'
                    f'</td>'
                )

            html.append(
                f'<td class="method-cell">'
                f'{method}'
                f'</td>'
            )

            for metric in metrics[:5]:

                html.append(
                    f"<td>{metric}</td>"
                )

            html.append("</tr>")

    html += [
        "</tbody>",
        "</table>",
        "</div>",
        "</div>",
    ]

    return "\n".join(
        html
    )


# ================================================================
# TABLE 2
# ================================================================


def parse_table2(
    tex_path: Path,
) -> tuple[str, list[dict]]:

    tex = tex_path.read_text(
        encoding="utf-8",
    )

    caption = parse_caption(
        tex
    )

    rows = extract_rows(
        tex
    )

    records = []

    current_dataset = ""
    current_size = ""

    for line in rows:

        # Ignore header.
        if (
            "Dataset" in line
            and "JScore" in line
        ):
            continue

        if (
            "R-1" in line
            and "B-1" in line
        ):
            continue

        cells = [
            c.strip()
            for c in line.split("&")
        ]

        # Logical table:
        #
        # dataset
        # size
        # method
        # jscore
        # R1
        # R2
        # RL
        # B1
        # B2
        # B3
        # B4

        while len(cells) < 11:
            cells.append("")

        cells = cells[:11]

        dataset_raw = cells[0]
        size_raw = cells[1]
        method_raw = cells[2]

        # Dataset.
        if dataset_raw:

            value = unwrap_multirow(
                dataset_raw
            )

            if value is None:
                value = dataset_raw

            current_dataset = clean_cell(
                value
            )

            current_size = ""

        # Size.
        if size_raw:

            value = unwrap_multirow(
                size_raw
            )

            if value is None:
                value = size_raw

            current_size = clean_cell(
                value
            )

        # Method.
        method = clean_cell(
            method_raw
        )

        if not method:
            continue

        values = [
            clean_cell(v)
            for v in cells[3:11]
        ]

        records.append(
            {
                "dataset": current_dataset,
                "size": current_size,
                "method": method,
                "values": values,
            }
        )

    return (
        caption,
        records,
    )


def run_length(
    records: list[dict],
    start: int,
    key: str,
    stop: int,
) -> int:

    value = records[start][key]

    end = start + 1

    while (
        end < stop
        and records[end][key] == value
    ):
        end += 1

    return (
        end - start
    )


def build_table2(
    tex_path: Path,
) -> str:

    caption, records = parse_table2(
        tex_path
    )

    html = [
        '<div class="result-table-wrap" id="table-vlm">',
        f'<p class="table-caption">{caption}</p>',
        '<div class="table-scroll">',
        '<table class="result-table vlm-table">',

        "<colgroup>",
        '<col class="c-dataset">',
        '<col class="c-size">',
        '<col class="c-method">',
        '<col class="c-jscore">',
        '<col class="c-metric">',
        '<col class="c-metric">',
        '<col class="c-metric">',
        '<col class="c-metric">',
        '<col class="c-metric">',
        '<col class="c-metric">',
        '<col class="c-metric">',
        "</colgroup>",

        "<thead>",

        "<tr>",
        '<th rowspan="2">Dataset</th>',
        '<th rowspan="2">Size</th>',
        '<th rowspan="2">Method</th>',
        '<th rowspan="2">JScore&nbsp;↑</th>',
        '<th colspan="3">ROUGE&nbsp;↑</th>',
        '<th colspan="4">BLEU&nbsp;↑</th>',
        "</tr>",

        "<tr>",
        "<th>R-1</th>",
        "<th>R-2</th>",
        "<th>R-L</th>",
        "<th>B-1</th>",
        "<th>B-2</th>",
        "<th>B-3</th>",
        "<th>B-4</th>",
        "</tr>",

        "</thead>",
        "<tbody>",
    ]

    i = 0

    while i < len(records):

        dataset = records[i]["dataset"]

        dataset_end = i + 1

        while (
            dataset_end < len(records)
            and records[dataset_end]["dataset"]
            == dataset
        ):
            dataset_end += 1

        dataset_span = (
            dataset_end - i
        )

        j = i

        while j < dataset_end:

            size_span = run_length(
                records,
                j,
                "size",
                dataset_end,
            )

            size_end = (
                j + size_span
            )

            for k in range(
                j,
                size_end,
            ):

                record = records[k]

                classes = [
                    row_class(
                        record["method"]
                    )
                ]

                if (
                    k == i
                    and i > 0
                ):
                    classes.append(
                        "dataset-start"
                    )

                if (
                    k == j
                    and j > i
                ):
                    classes.append(
                        "size-start"
                    )

                html.append(
                    '<tr class="'
                    + " ".join(classes)
                    + '">'
                )

                # Dataset cell.
                if k == i:

                    html.append(
                        f'<td rowspan="{dataset_span}" '
                        f'class="dataset-cell">'
                        f'{dataset}'
                        f'</td>'
                    )

                # Size cell.
                if k == j:

                    html.append(
                        f'<td rowspan="{size_span}" '
                        f'class="size-cell">'
                        f'{record["size"]}'
                        f'</td>'
                    )

                # Method.
                html.append(
                    '<td class="method-cell">'
                    f'{record["method"]}'
                    '</td>'
                )

                for value in record["values"]:

                    html.append(
                        '<td class="metric-cell">'
                        f'{value}'
                        '</td>'
                    )

                html.append(
                    "</tr>"
                )

            j = size_end

        i = dataset_end

    html += [
        "</tbody>",
        "</table>",
        "</div>",
        "</div>",
    ]

    return "\n".join(
        html
    )


# ================================================================
# CSS
# ================================================================


CSS = """
<style>

:root {
    --ov-accent: #5b5bd6;
    --ov-soft: #eeeeff;
    --ov-head: #2b2d42;
    --ov-border: #e2e3ed;
    --ov-ref: #f3f3f5;
}


/* ============================================================= */
/* CONTAINER                                                     */
/* ============================================================= */

.result-table-wrap {
    width: 100%;
    max-width: 100%;
    margin: 2.25rem auto 3rem;
}

.table-caption {
    margin: 0 auto 1rem;
    max-width: 900px;

    text-align: center;
    font-size: 0.9rem;
    line-height: 1.45;
    color: #3a3a44;
}


/*
 * IMPORTANT:
 *
 * No horizontal scrolling.
 */
.table-scroll {
    width: 100%;
    overflow: hidden;

    border: 1px solid var(--ov-border);
    border-radius: 14px;

    box-shadow:
        0 6px 24px
        rgba(30, 30, 60, 0.07);
}


/* ============================================================= */
/* SHARED TABLE                                                  */
/* ============================================================= */

.result-table {
    width: 100%;

    border-collapse: separate;
    border-spacing: 0;

    table-layout: fixed;

    font-family:
        Inter,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;

    font-size:
        clamp(
            0.62rem,
            0.77vw,
            0.78rem
        );

    font-variant-numeric:
        tabular-nums;

    color: #30303a;
}

.result-table th,
.result-table td {
    padding:
        7px 6px;

    text-align: center;
    vertical-align: middle;

    border-bottom:
        1px solid
        var(--ov-border);

    overflow: hidden;
    text-overflow: clip;
}


/* ============================================================= */
/* HEADER                                                        */
/* ============================================================= */

.result-table thead th {
    background:
        var(--ov-head);

    color: #fff;

    font-weight: 600;

    line-height: 1.15;

    letter-spacing: 0.01em;
}

.result-table thead tr:first-child th {
    border-bottom:
        1px solid
        rgba(
            255,
            255,
            255,
            0.18
        );
}


/* ============================================================= */
/* DATASET                                                       */
/* ============================================================= */

.result-table .dataset-cell {
    background: #f7f7fb;

    color: #28293d;

    font-weight: 700;
    font-style: italic;

    text-align: left;

    white-space: normal;

    padding-left: 12px;

    border-right:
        1px solid
        var(--ov-border);
}


/* ============================================================= */
/* METHOD                                                        */
/* ============================================================= */

.result-table .method-cell {
    text-align: left;

    padding-left: 12px;

    font-weight: 500;

    white-space: normal;

    overflow-wrap: anywhere;
}


/* ============================================================= */
/* BASE ROWS                                                     */
/* ============================================================= */

.result-table tbody tr.row-base:nth-of-type(even) td:not(.dataset-cell) {
    background: #fbfbfc;
}


/* ============================================================= */
/* GEMINI / REFERENCE                                            */
/* ============================================================= */

.result-table tbody tr.row-ref td:not(.dataset-cell) {
    background:
        var(--ov-ref);
}


/* ============================================================= */
/* OPENVAM                                                       */
/* ============================================================= */

.result-table tbody tr.row-openvam td:not(.dataset-cell):not(.size-cell) {
    background:
        var(--ov-soft);
}

.result-table tbody tr.row-openvam .method-cell {
    color:
        var(--ov-accent);

    font-weight: 700;
}


/* ============================================================= */
/* BEST VALUES                                                   */
/* ============================================================= */

.result-table strong {
    color:
        var(--ov-accent);

    font-weight: 700;
}


/* ============================================================= */
/* GROUP SEPARATORS                                              */
/* ============================================================= */

.result-table tbody tr.size-start td {
    border-top:
        1px solid
        #cacbd7;
}

.result-table tbody tr.dataset-start td {
    border-top:
        2px solid
        #bcbeca;
}


/* ============================================================= */
/* TABLE 2                                                       */
/* ============================================================= */

/*
 * These widths add to 100%.
 *
 * Dataset  = 10%
 * Size     = 8%
 * Method   = 18%
 * JScore   = 9%
 * 7 metric columns = ~7.85% each
 */

#table-vlm .c-dataset {
    width: 10%;
}

#table-vlm .c-size {
    width: 8%;
}

#table-vlm .c-method {
    width: 18%;
}

#table-vlm .c-jscore {
    width: 9%;
}

#table-vlm .c-metric {
    width: 7.85%;
}


/*
 * Size uses the same soft dataset-like appearance.
 */
#table-vlm .size-cell {
    background: #fafafd;

    text-align: center;

    font-weight: 500;

    white-space: normal;

    border-right:
        1px solid
        var(--ov-border);
}


/*
 * Keep numerical values on one line.
 */
#table-vlm .metric-cell {
    white-space: nowrap;

    padding-left: 3px;
    padding-right: 3px;
}


/*
 * Prevent long methods from forcing the table wider.
 */
#table-vlm .method-cell {
    white-space: normal;

    overflow-wrap: anywhere;

    word-break: normal;
}


/*
 * No minimum width!
 *
 * A min-width here would reintroduce horizontal scrolling.
 */
#table-vlm .vlm-table {
    min-width: 0;
    width: 100%;
}


/* ============================================================= */
/* SMALLER SCREENS                                               */
/* ============================================================= */

@media (max-width: 1000px) {

    #table-vlm .result-table {
        font-size: 0.67rem;
    }

    #table-vlm .result-table th,
    #table-vlm .result-table td {
        padding:
            6px 3px;
    }

    #table-vlm .method-cell {
        padding-left: 7px;
    }

}


@media (max-width: 750px) {

    #table-vlm .result-table {
        font-size: 0.56rem;
    }

    #table-vlm .result-table th,
    #table-vlm .result-table td {
        padding:
            5px 2px;
    }

    #table-vlm .dataset-cell {
        padding-left: 5px;
    }

    #table-vlm .method-cell {
        padding-left: 4px;
    }

}

</style>
"""


# ================================================================
# Main
# ================================================================


def main() -> None:

    root = Path(
        __file__
    ).resolve().parent

    table1_path = (
        root / "main_table1.tex"
    )

    table2_path = (
        root / "main_table2.tex"
    )

    if not table1_path.exists():

        raise FileNotFoundError(
            f"Could not find: "
            f"{table1_path}"
        )

    if not table2_path.exists():

        raise FileNotFoundError(
            f"Could not find: "
            f"{table2_path}"
        )

    table1 = build_table1(
        table1_path
    )

    table2 = build_table2(
        table2_path
    )

    tables = (
        CSS
        + table1
        + table2
    )

    OUT.write_text(
        tables,
        encoding="utf-8",
    )

    print(
        "Wrote",
        OUT,
    )

    # ------------------------------------------------------------
    # Inline into index.html
    # ------------------------------------------------------------

    index_path = (
        root / "index.html"
    )

    if not index_path.exists():
        return

    index = index_path.read_text(
        encoding="utf-8",
    )

    start = (
        "<!-- TABLES:START -->"
    )

    end = (
        "<!-- TABLES:END -->"
    )

    if (
        start not in index
        or end not in index
    ):

        print(
            "TABLES markers not found "
            "in index.html"
        )

        return

    before = index.split(
        start,
        1,
    )[0]

    after = index.split(
        end,
        1,
    )[1]

    index = (
        before
        + start
        + "\n"
        + tables
        + "\n"
        + end
        + after
    )

    index_path.write_text(
        index,
        encoding="utf-8",
    )

    print(
        "Inlined tables into",
        index_path,
    )


if __name__ == "__main__":
    main()