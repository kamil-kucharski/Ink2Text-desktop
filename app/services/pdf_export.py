from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
import re

from PySide6 import QtCore


@dataclass(slots=True)
class PDFExportPayload:
    title: str
    content: str
    content_html: str | None = None


def build_note_html(payload: PDFExportPayload) -> str:
    if payload.content_html is not None:
        body_html = convert_note_content_to_html(payload.content_html, "html")
    else:
        body_html = convert_note_content_to_html(payload.content, "plain")

    return f"""<!DOCTYPE html>
<html lang="pl">
  <head>
    <meta charset="utf-8" />
    <style>
      body {{
        font-family: "DejaVu Sans", Arial, sans-serif;
        color: #1b1f23;
        margin: 22px 24px;
        line-height: 1.5;
        font-size: 9.5pt;
      }}
      h1 {{
        font-size: 15.5px;
        margin: 18px 0 8px 0;
        color: #111827;
      }}
      h2 {{
        font-size: 13.5px;
        margin: 16px 0 7px 0;
        color: #1f2937;
      }}
      h3 {{
        font-size: 12px;
        margin: 14px 0 6px 0;
        color: #374151;
      }}
      h4 {{
        font-size: 10.5px;
        margin: 12px 0 5px 0;
        color: #4b5563;
      }}
      h5 {{
        font-size: 9.5px;
        margin: 10px 0 5px 0;
        color: #4b5563;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }}
      h6 {{
        font-size: 9px;
        margin: 9px 0 4px 0;
        color: #6b7280;
        font-style: italic;
      }}
      p {{
        margin: 0 0 8px 0;
      }}
      ul, ol {{
        margin: 0 0 10px 14px;
        padding-left: 12px;
      }}
      li {{
        margin-bottom: 3px;
      }}
      strong {{
        font-weight: 700;
        color: #111827;
      }}
      em {{
        font-style: italic;
      }}
      code {{
        font-family: "DejaVu Sans Mono", "Courier New", monospace;
        background: #f3f4f6;
        padding: 1px 4px;
        border-radius: 4px;
      }}
      .math-inline {{
        font-family: "DejaVu Serif", "Times New Roman", serif;
      }}
      .math-frac {{
        white-space: nowrap;
      }}
      .math-frac sup,
      .math-frac sub {{
        font-size: 75%;
      }}
    </style>
  </head>
  <body>
    {body_html}
  </body>
</html>
"""


def export_note_to_pdf(
    pdf_path: Path,
    payload: PDFExportPayload,
    text_document_factory=None,
    pdf_writer_factory=None,
) -> Path:
    try:
        from PySide6 import QtGui
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "Brakuje modułów Qt potrzebnych do eksportu PDF. "
            "Upewnij się, że PySide6 jest poprawnie zainstalowane."
        ) from error

    document_factory = text_document_factory or QtGui.QTextDocument
    effective_pdf_writer_factory = pdf_writer_factory or QtGui.QPdfWriter

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    document = document_factory()
    document.setHtml(build_note_html(payload))
    document.setDocumentMargin(8)

    writer = effective_pdf_writer_factory(str(pdf_path))
    writer.setResolution(300)
    writer.setTitle(payload.title.strip() or "Bez tytułu")
    writer.setCreator("Ink2Text")
    margins = QtCore.QMarginsF(10, 10, 10, 10)
    writer.setPageMargins(margins, QtGui.QPageLayout.Unit.Millimeter)

    print_method = getattr(document, "print_", None) or getattr(document, "print", None)
    if print_method is None:
        raise RuntimeError("Bieżąca wersja Qt nie udostępnia metody eksportu dokumentu do PDF.")

    print_method(writer)
    return pdf_path


def _plain_text_to_html(content: str) -> str:
    lines = content.splitlines()
    if not lines:
        return "<p></p>"

    html_parts: list[str] = []
    paragraph_buffer: list[str] = []
    list_buffer: list[str] = []
    current_list_type: str | None = None

    def flush_paragraph() -> None:
        if paragraph_buffer:
            paragraph_text = "<br />".join(_render_inline_formatting(line) for line in paragraph_buffer)
            html_parts.append(f"<p>{paragraph_text}</p>")
            paragraph_buffer.clear()

    def flush_list() -> None:
        nonlocal current_list_type
        if list_buffer and current_list_type:
            tag = "ol" if current_list_type == "ordered" else "ul"
            items = "".join(f"<li>{_render_inline_formatting(item)}</li>" for item in list_buffer)
            html_parts.append(f"<{tag}>{items}</{tag}>")
            list_buffer.clear()
            current_list_type = None

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            flush_list()
            continue

        if _is_markdown_separator(stripped):
            flush_paragraph()
            flush_list()
            continue

        ordered_prefix = _extract_ordered_list_item(stripped)
        unordered_prefix = _extract_unordered_list_item(stripped)
        heading = _extract_heading(stripped)

        if heading is not None:
            flush_paragraph()
            flush_list()
            level, heading_text = heading
            html_parts.append(f"<h{level}>{_render_inline_formatting(heading_text)}</h{level}>")
            continue

        if ordered_prefix is not None:
            flush_paragraph()
            if current_list_type not in {None, "ordered"}:
                flush_list()
            current_list_type = "ordered"
            list_buffer.append(ordered_prefix)
            continue

        if unordered_prefix is not None:
            flush_paragraph()
            if current_list_type not in {None, "unordered"}:
                flush_list()
            current_list_type = "unordered"
            list_buffer.append(unordered_prefix)
            continue

        flush_list()
        paragraph_buffer.append(stripped)

    flush_paragraph()
    flush_list()

    return "\n".join(html_parts) if html_parts else "<p></p>"


def convert_note_content_to_html(content: str, content_format: str) -> str:
    normalized_content = content.strip()
    if not normalized_content:
        return "<p></p>"

    if content_format == "html":
        return _render_math_in_html(_remove_separator_html(_extract_body_html(content)))

    return _plain_text_to_html(content)


def convert_note_content_to_editor_html(content: str, content_format: str) -> str:
    if content_format == "html":
        body_html = _render_math_in_html(_extract_body_html(content))
    else:
        body_html = _plain_text_to_html(content)

    editor_body = _replace_heading_tags_for_editor(body_html)
    return f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
  </head>
  <body style="font-family: 'DejaVu Sans'; font-size: 9.5pt; line-height: 1.45;">
    {editor_body}
  </body>
</html>
"""


def _extract_unordered_list_item(line: str) -> str | None:
    prefixes = ("- ", "* ", "• ")
    for prefix in prefixes:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def _extract_ordered_list_item(line: str) -> str | None:
    if ". " not in line:
        return None

    number_part, text_part = line.split(". ", 1)
    if number_part.isdigit():
        return text_part.strip()
    return None


def _extract_body_html(html: str) -> str:
    match = re.search(r"<body[^>]*>(.*)</body>", html, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip() or "<p></p>"
    return html.strip() or "<p></p>"


def _replace_heading_tags_for_editor(html: str) -> str:
    heading_styles = {
        "1": "font-size: 15.5pt; font-weight: 700; margin: 14px 0 7px 0;",
        "2": "font-size: 13.5pt; font-weight: 700; margin: 12px 0 6px 0;",
        "3": "font-size: 12pt; font-weight: 700; margin: 10px 0 5px 0;",
        "4": "font-size: 10.5pt; font-weight: 700; margin: 9px 0 5px 0;",
        "5": "font-size: 9.5pt; font-weight: 700; margin: 8px 0 4px 0;",
        "6": "font-size: 9pt; font-weight: 700; margin: 7px 0 4px 0;",
    }

    def replace_heading(match: re.Match[str]) -> str:
        level = match.group(1)
        inner_html = match.group(2).strip() or "&nbsp;"
        style = heading_styles[level]
        return f'<p style="{style}">{inner_html}</p>'

    return re.sub(
        r"<h([1-6])[^>]*>(.*?)</h\1>",
        replace_heading,
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _extract_heading(line: str) -> tuple[int, str] | None:
    match = re.match(r"^(#{1,6})\s+(.*)$", line)
    if not match:
        return None

    level = len(match.group(1))
    text = match.group(2).strip()
    if not text:
        return None
    return level, text


def _render_inline_formatting(text: str) -> str:
    escaped = escape(text)
    escaped = re.sub(r"\$([^$]+)\$", lambda match: _render_inline_math(match.group(1)), escaped)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    escaped = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"<em>\1</em>", escaped)
    return escaped


def _render_inline_math(expression: str) -> str:
    rendered = _render_math_expression(expression.strip())
    return f'<span class="math-inline">{rendered}</span>'


def _render_math_expression(expression: str) -> str:
    rendered = _render_math_alphabets(expression)
    rendered = _render_fractions(rendered)
    rendered = _render_roots(rendered)
    rendered = _render_text_commands(rendered)
    rendered = _render_scripts(rendered)
    rendered = _replace_latex_symbols(rendered)
    rendered = _cleanup_latex_spacing(rendered)
    rendered = _cleanup_unknown_latex(rendered)
    return rendered


def _render_math_fragment(expression: str) -> str:
    rendered = _render_math_alphabets(expression.strip())
    rendered = _render_roots(rendered)
    rendered = _render_text_commands(rendered)
    rendered = _render_scripts(rendered)
    rendered = _replace_latex_symbols(rendered)
    rendered = _cleanup_latex_spacing(rendered)
    rendered = _cleanup_unknown_latex(rendered)
    return rendered


def _render_math_alphabets(expression: str) -> str:
    blackboard_bold = {
        "A": "𝔸",
        "B": "𝔹",
        "C": "ℂ",
        "D": "𝔻",
        "E": "𝔼",
        "F": "𝔽",
        "G": "𝔾",
        "H": "ℍ",
        "I": "𝕀",
        "J": "𝕁",
        "K": "𝕂",
        "L": "𝕃",
        "M": "𝕄",
        "N": "ℕ",
        "O": "𝕆",
        "P": "ℙ",
        "Q": "ℚ",
        "R": "ℝ",
        "S": "𝕊",
        "T": "𝕋",
        "U": "𝕌",
        "V": "𝕍",
        "W": "𝕎",
        "X": "𝕏",
        "Y": "𝕐",
        "Z": "ℤ",
    }

    def replace_braced(match: re.Match[str]) -> str:
        return "".join(blackboard_bold.get(char, char) for char in match.group(1))

    def replace_single(match: re.Match[str]) -> str:
        return blackboard_bold.get(match.group(1), match.group(1))

    rendered = re.sub(r"\\mathbb\{([^{}]+)\}", replace_braced, expression)
    rendered = re.sub(r"\\mathbb\s+([A-Za-z])", replace_single, rendered)
    return rendered


def _render_roots(expression: str) -> str:
    rendered = re.sub(
        r"\\sqrt\[([^{}\[\]]+)\]\{([^{}]+)\}",
        lambda match: f'<sup>{_render_math_fragment(match.group(1))}</sup>√({_render_math_fragment(match.group(2))})',
        expression,
    )
    return re.sub(
        r"\\sqrt\{([^{}]+)\}",
        lambda match: f"√({_render_math_fragment(match.group(1))})",
        rendered,
    )


def _render_text_commands(expression: str) -> str:
    commands = (
        "text",
        "textrm",
        "textit",
        "textbf",
        "mathrm",
        "mathbf",
        "mathit",
        "mathsf",
        "mathtt",
        "operatorname",
        "overline",
        "underline",
        "hat",
        "bar",
        "vec",
        "tilde",
    )
    command_pattern = "|".join(commands)
    return re.sub(
        rf"\\(?:{command_pattern})\{{([^{{}}]+)\}}",
        lambda match: _render_math_fragment(match.group(1)),
        expression,
    )


def _render_fractions(expression: str) -> str:
    pattern = re.compile(r"\\(?:frac|dfrac|tfrac)\{([^{}]*)\}\{([^{}]*)\}")

    def replace_fraction(match: re.Match[str]) -> str:
        numerator = _render_math_fragment(match.group(1))
        denominator = _render_math_fragment(match.group(2))
        return (
            '<span class="math-frac" style="white-space: nowrap;">'
            f'<sup style="font-size: 75%;">{numerator}</sup>'
            "&frasl;"
            f'<sub style="font-size: 75%;">{denominator}</sub>'
            "</span>"
        )

    previous = None
    rendered = expression
    while rendered != previous:
        previous = rendered
        rendered = pattern.sub(replace_fraction, rendered)
    return rendered


def _render_scripts(expression: str) -> str:
    token = r"(\\[A-Za-z]+|[A-Za-z0-9Α-ω\)\]])"

    def replace_superscript(match: re.Match[str]) -> str:
        base = _replace_latex_symbols(match.group(1))
        exponent = _replace_latex_symbols(match.group(2).strip())
        return f"{base}<sup>{exponent}</sup>"

    def replace_subscript(match: re.Match[str]) -> str:
        base = _replace_latex_symbols(match.group(1))
        index = _replace_latex_symbols(match.group(2).strip())
        return f"{base}<sub>{index}</sub>"

    rendered = re.sub(rf"{token}\^\{{([^{{}}]+)\}}", replace_superscript, expression)
    rendered = re.sub(rf"{token}\^\(([^()]+)\)", replace_superscript, rendered)
    rendered = re.sub(rf"{token}\^([A-Za-z0-9+\-=])", replace_superscript, rendered)
    rendered = re.sub(rf"{token}_\{{([^{{}}]+)\}}", replace_subscript, rendered)
    rendered = re.sub(rf"{token}_\(([^()]+)\)", replace_subscript, rendered)
    rendered = re.sub(rf"{token}_([A-Za-z0-9+\-=])", replace_subscript, rendered)
    rendered = re.sub(rf"{token}_(?:&#x27;|&quot;|&apos;)([A-Za-z0-9+\-=]+)(?:&#x27;|&quot;|&apos;)", replace_subscript, rendered)
    return rendered


def _replace_latex_symbols(expression: str) -> str:
    replacements = {
        r"\sin": "sin",
        r"\cos": "cos",
        r"\tan": "tan",
        r"\cot": "cot",
        r"\sec": "sec",
        r"\csc": "csc",
        r"\log": "log",
        r"\ln": "ln",
        r"\lim": "lim",
        r"\min": "min",
        r"\max": "max",
        r"\sup": "sup",
        r"\inf": "inf",
        r"\deg": "deg",
        r"\det": "det",
        r"\to": "&rarr;",
        r"\rightarrow": "&rarr;",
        r"\leftarrow": "&larr;",
        r"\leftrightarrow": "&harr;",
        r"\mapsto": "↦",
        r"\Rightarrow": "&rArr;",
        r"\Leftarrow": "&lArr;",
        r"\Leftrightarrow": "&hArr;",
        r"\langle": "⟨",
        r"\rangle": "⟩",
        r"\lceil": "⌈",
        r"\rceil": "⌉",
        r"\lfloor": "⌊",
        r"\rfloor": "⌋",
        r"\lVert": "‖",
        r"\rVert": "‖",
        r"\Vert": "‖",
        r"\|": "‖",
        r"\{": "__MATH_LBRACE__",
        r"\}": "__MATH_RBRACE__",
        r"\geq": "&ge;",
        r"\ge": "&ge;",
        r"\leq": "&le;",
        r"\le": "&le;",
        r"\neq": "&ne;",
        r"\ne": "&ne;",
        r"\equiv": "&equiv;",
        r"\sim": "&sim;",
        r"\simeq": "&simeq;",
        r"\cong": "&cong;",
        r"\times": "&times;",
        r"\cdot": "&middot;",
        r"\div": "&divide;",
        r"\pm": "&plusmn;",
        r"\mp": "&#8723;",
        r"\approx": "&asymp;",
        r"\infty": "&infin;",
        r"\sqrt": "&radic;",
        r"\sum": "&sum;",
        r"\prod": "&prod;",
        r"\int": "&int;",
        r"\partial": "&part;",
        r"\nabla": "&nabla;",
        r"\in": "&isin;",
        r"\notin": "&notin;",
        r"\subset": "&sub;",
        r"\subseteq": "&sube;",
        r"\supset": "&sup;",
        r"\supseteq": "&supe;",
        r"\cup": "&cup;",
        r"\cap": "&cap;",
        r"\emptyset": "&empty;",
        r"\forall": "&forall;",
        r"\exists": "&exist;",
        r"\neg": "&not;",
        r"\land": "&and;",
        r"\wedge": "&and;",
        r"\lor": "&or;",
        r"\vee": "&or;",
        r"\alpha": "&alpha;",
        r"\beta": "&beta;",
        r"\gamma": "&gamma;",
        r"\delta": "&delta;",
        r"\epsilon": "&epsilon;",
        r"\varepsilon": "&epsilon;",
        r"\zeta": "&zeta;",
        r"\eta": "&eta;",
        r"\theta": "&theta;",
        r"\vartheta": "&theta;",
        r"\iota": "&iota;",
        r"\kappa": "&kappa;",
        r"\lambda": "&lambda;",
        r"\mu": "&mu;",
        r"\nu": "&nu;",
        r"\xi": "&xi;",
        r"\omicron": "&omicron;",
        r"\pi": "&pi;",
        r"\rho": "&rho;",
        r"\sigma": "&sigma;",
        r"\tau": "&tau;",
        r"\upsilon": "&upsilon;",
        r"\phi": "&phi;",
        r"\varphi": "&phi;",
        r"\chi": "&chi;",
        r"\psi": "&psi;",
        r"\omega": "&omega;",
        r"\Gamma": "&Gamma;",
        r"\Delta": "&Delta;",
        r"\Theta": "&Theta;",
        r"\Lambda": "&Lambda;",
        r"\Xi": "&Xi;",
        r"\Pi": "&Pi;",
        r"\Sigma": "&Sigma;",
        r"\Phi": "&Phi;",
        r"\Psi": "&Psi;",
        r"\Omega": "&Omega;",
    }

    rendered = expression
    for source in sorted(replacements, key=len, reverse=True):
        rendered = rendered.replace(source, replacements[source])
    return rendered


def _cleanup_latex_spacing(expression: str) -> str:
    rendered = expression
    spacing = {
        r"\,": " ",
        r"\;": " ",
        r"\:": " ",
        r"\!": "",
        r"\ ": " ",
        "~": " ",
    }
    for source, target in spacing.items():
        rendered = rendered.replace(source, target)
    rendered = rendered.replace(r"\left", "").replace(r"\right", "")
    return rendered


def _cleanup_unknown_latex(expression: str) -> str:
    rendered = expression
    rendered = re.sub(r"\\([{}#$%&_])", r"\1", rendered)
    rendered = rendered.replace(r"\\", " ")
    rendered = re.sub(
        r"\\[A-Za-z]+\{([^{}]*)\}",
        lambda match: _render_math_fragment(match.group(1)),
        rendered,
    )
    rendered = re.sub(r"\\([A-Za-z]+)", r"\1", rendered)
    rendered = rendered.replace("{", "").replace("}", "")
    rendered = rendered.replace("__MATH_LBRACE__", "{").replace("__MATH_RBRACE__", "}")
    rendered = re.sub(r"\s{2,}", " ", rendered)
    return rendered.strip()


def _render_math_in_html(html: str) -> str:
    return re.sub(r"\$([^$]+)\$", lambda match: _render_inline_math(match.group(1)), html)


def _is_markdown_separator(line: str) -> bool:
    return bool(re.fullmatch(r"(?:-{3,}|\*{3,}|_{3,})", line.strip()))


def _remove_separator_html(html: str) -> str:
    html = re.sub(r"<hr\s*/?>", "", html, flags=re.IGNORECASE)
    return re.sub(
        r"<p[^>]*>\s*(?:-{3,}|\*{3,}|_{3,})\s*</p>",
        "",
        html,
        flags=re.IGNORECASE,
    )
