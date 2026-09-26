"""Convert OpenVAM LaTeX sections to paper.txt and paper-content.html."""
from __future__ import annotations

import re
from pathlib import Path

SECTIONS_DIR = Path(r"c:\Users\My_PC\Documents\GitHub\OpenVAM\sections")
OUT_DIR = Path(__file__).resolve().parent

ORDER = [
    "1_abstract.tex",
    "2_intro.tex",
    "3_related.tex",
    "4_method.tex",
    "5_exp.tex",
    "6_ablation.tex",
    "7_conclusion.tex",
]


def strip_environments(text: str) -> str:
    for env in ("figure", "figure*", "table", "table*", "itemize", "enumerate"):
        text = re.sub(
            rf"\\begin\{{{env}\}}[\s\S]*?\\end\{{{env}\}}",
            "",
            text,
            flags=re.MULTILINE,
        )
    text = re.sub(r"\\input\{[^}]+\}", "", text)
    text = re.sub(r"\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}", "", text)
    text = re.sub(r"\\resizebox\{[^}]+\}\{[^}]+\}\{%", "", text)
    text = re.sub(r"\\vspace\{[^}]+\}", "", text)
    text = re.sub(r"\\label\{[^}]+\}", "", text)
    text = re.sub(r"\\cite\{[^}]+\}", "", text)
    text = re.sub(r"\\autoref\{[^}]+\}", "", text)
    text = re.sub(r"\\ref\{[^}]+\}", "", text)
    text = re.sub(r"\\footnote\{[^}]+\}", "", text)
    text = re.sub(r"\\noindent", "", text)
    text = re.sub(r"\\small\b", "", text)
    text = re.sub(r"\\footnotesize\b", "", text)
    text = re.sub(r"\\centering\b", "", text)
    text = re.sub(r"\\caption\{[^}]*\}", "", text)
    text = re.sub(r"%.*", "", text)
    return text


def latex_to_html(text: str) -> str:
    text = strip_environments(text)
    text = re.sub(r"\\section\{([^}]+)\}", r'<h2 class="title is-3">\1</h2>', text)
    text = re.sub(r"\\subsection\{([^}]+)\}", r'<h3 class="title is-4">\1</h3>', text)
    text = re.sub(r"\\textbf\{([^}]+)\}", r"<strong>\1</strong>", text)
    text = re.sub(r"\\emph\{([^}]+)\}", r"<em>\1</em>", text)
    text = re.sub(r"\\textit\{([^}]+)\}", r"<em>\1</em>", text)
    text = re.sub(r"\\texttt\{([^}]+)\}", r"<code>\1</code>", text)
    text = re.sub(r"\$([^$]+)\$", r"\\(\1\\)", text)
    text = re.sub(r"~", " ", text)
    text = re.sub(r"\\,", " ", text)
    text = re.sub(r"\\quad", " ", text)
    text = re.sub(r"\\middle\|", "|", text)
    text = re.sub(r"\\left|\\right", "", text)
    text = re.sub(r"\\!", "", text)
    text = re.sub(r"\\,", "", text)
    text = re.sub(r"\\;", "", text)
    text = re.sub(r"\\textsubscript\{[^}]+\}", "", text)
    text = re.sub(r"\\textcolor\{[^}]+\}\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\\underline\{([^}]+)\}", r"\1", text)

    blocks: list[str] = []
    for block in re.split(r"\n\s*\n", text.strip()):
        block = block.strip()
        if not block:
            continue
        if block.startswith("<h2") or block.startswith("<h3"):
            blocks.append(block)
            continue
        if "\\begin{equation" in block or "\\begin{align" in block:
            eq = block
            eq = re.sub(r"\\begin\{equation\*?\}|\\end\{equation\*?\}", "", eq)
            eq = re.sub(r"\\begin\{align\*?\}|\\end\{align\*?\}", "", eq)
            eq = eq.strip()
            blocks.append(f'<div class="equation-block">\\[{eq}\\]</div>')
            continue
        block = re.sub(r"\s+", " ", block)
        blocks.append(f'<p>{block}</p>')

    return "\n".join(blocks)


def latex_to_plain(text: str) -> str:
    text = strip_environments(text)
    text = re.sub(r"\\section\{([^}]+)\}", r"\n\n# \1\n\n", text)
    text = re.sub(r"\\subsection\{([^}]+)\}", r"\n\n## \1\n\n", text)
    text = re.sub(r"\\textbf\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\\emph\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\\textit\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\\texttt\{([^}]+)\}", r"\1", text)
    text = re.sub(r"\$([^$]+)\$", r"\1", text)
    text = re.sub(r"\\begin\{equation\*?\}|\\end\{equation\*?\}", "\n", text)
    text = re.sub(r"\\begin\{align\*?\}|\\end\{align\*?\}", "\n", text)
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = re.sub(r"[{}]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


def main() -> None:
    combined_tex = []
    html_parts = ['<div class="content has-text-justified">']
    plain_parts = []

    for name in ORDER:
        path = SECTIONS_DIR / name
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8")
        combined_tex.append(raw)
        if name == "1_abstract.tex":
            continue
        html_parts.append(latex_to_html(raw))
        plain_parts.append(latex_to_plain(raw))

    html_parts.append("</div>")
    (OUT_DIR / "paper-content.html").write_text("\n".join(html_parts), encoding="utf-8")

    abstract = latex_to_plain((SECTIONS_DIR / "1_abstract.tex").read_text(encoding="utf-8"))
    abstract = re.sub(r"\\begin\{abstract\}|\\end\{abstract\}", "", abstract).strip()
    plain = abstract + "\n\n" + "\n\n".join(plain_parts)
    (OUT_DIR / "paper.txt").write_text(plain, encoding="utf-8")
    print("Wrote paper.txt and paper-content.html")


if __name__ == "__main__":
    main()
