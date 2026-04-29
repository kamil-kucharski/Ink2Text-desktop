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
    title_html = _build_title_html(payload.title)

    return f"""<!DOCTYPE html>
<html lang="pl">
  <head>
    <meta charset="utf-8" />
    <style>
      body {{
        font-family: "DejaVu Sans", Arial, sans-serif;
        color: #1b1f23;
        margin: 42px 48px;
        line-height: 1.6;
        font-size: 12pt;
      }}
      .note-title {{
        font-size: 26px;
        margin: 0 0 24px 0;
        border-bottom: 1px solid #d9dee3;
        padding-bottom: 14px;
        color: #111827;
      }}
      h1 {{
        font-size: 22px;
        margin: 28px 0 12px 0;
        color: #111827;
      }}
      h2 {{
        font-size: 18px;
        margin: 24px 0 10px 0;
        color: #1f2937;
      }}
      h3 {{
        font-size: 15px;
        margin: 20px 0 8px 0;
        color: #374151;
      }}
      h4 {{
        font-size: 13px;
        margin: 18px 0 8px 0;
        color: #4b5563;
      }}
      h5 {{
        font-size: 12px;
        margin: 16px 0 6px 0;
        color: #4b5563;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }}
      h6 {{
        font-size: 11px;
        margin: 14px 0 6px 0;
        color: #6b7280;
        font-style: italic;
      }}
      p {{
        margin: 0 0 12px 0;
      }}
      ul, ol {{
        margin: 0 0 16px 20px;
        padding-left: 18px;
      }}
      li {{
        margin-bottom: 6px;
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
    </style>
  </head>
  <body>
    {title_html}
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
    document.setDocumentMargin(24)

    writer = effective_pdf_writer_factory(str(pdf_path))
    writer.setResolution(300)
    writer.setTitle(payload.title.strip() or "Bez tytułu")
    writer.setCreator("Notatki AI Desktop")
    margins = QtCore.QMarginsF(16, 16, 16, 16)
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
        return _extract_body_html(content)

    return _plain_text_to_html(content)


def convert_note_content_to_editor_html(content: str, content_format: str) -> str:
    if content_format == "html":
        body_html = _extract_body_html(content)
    else:
        body_html = _plain_text_to_html(content)

    editor_body = _replace_heading_tags_for_editor(body_html)
    return f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
  </head>
  <body style="font-family: 'DejaVu Sans'; font-size: 12pt; line-height: 1.45;">
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
        "1": "font-size: 22pt; font-weight: 700; margin: 18px 0 10px 0;",
        "2": "font-size: 18pt; font-weight: 700; margin: 16px 0 8px 0;",
        "3": "font-size: 15pt; font-weight: 700; margin: 14px 0 8px 0;",
        "4": "font-size: 13pt; font-weight: 700; margin: 12px 0 6px 0;",
        "5": "font-size: 12pt; font-weight: 700; margin: 10px 0 6px 0;",
        "6": "font-size: 11pt; font-weight: 700; margin: 8px 0 6px 0;",
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


def _build_title_html(title: str) -> str:
    cleaned_title = title.strip()
    if not cleaned_title or re.fullmatch(r"Notatka\s+\d+", cleaned_title, flags=re.IGNORECASE):
        return ""

    return f'<div class="note-title">{escape(cleaned_title)}</div>'


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
    replacements = {
        r"\to": "&rarr;",
        r"\rightarrow": "&rarr;",
        r"\leftarrow": "&larr;",
        r"\Rightarrow": "&rArr;",
        r"\Leftarrow": "&lArr;",
        r"\leftrightarrow": "&harr;",
        r"\geq": "&ge;",
        r"\leq": "&le;",
        r"\neq": "&ne;",
        r"\times": "&times;",
        r"\cdot": "&middot;",
        r"\pm": "&plusmn;",
        r"\approx": "&asymp;",
        r"\infty": "&infin;",
        r"\alpha": "&alpha;",
        r"\beta": "&beta;",
        r"\gamma": "&gamma;",
        r"\delta": "&delta;",
        r"\lambda": "&lambda;",
        r"\mu": "&mu;",
        r"\pi": "&pi;",
        r"\sigma": "&sigma;",
        r"\theta": "&theta;",
        r"\omega": "&omega;",
    }

    rendered = expression.strip()
    for source, target in replacements.items():
        rendered = rendered.replace(source, target)

    return f'<span class="math-inline">{rendered}</span>'
