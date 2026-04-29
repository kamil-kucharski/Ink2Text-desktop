from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path


@dataclass(slots=True)
class PDFExportPayload:
    title: str
    content: str


def build_note_html(payload: PDFExportPayload) -> str:
    title = escape(payload.title.strip() or "Bez tytułu")
    body_html = _plain_text_to_html(payload.content)

    return f"""<!DOCTYPE html>
<html lang="pl">
  <head>
    <meta charset="utf-8" />
    <style>
      body {{
        font-family: "DejaVu Sans", Arial, sans-serif;
        color: #1f1f1f;
        margin: 32px;
        line-height: 1.45;
      }}
      h1 {{
        font-size: 24px;
        margin: 0 0 20px 0;
        border-bottom: 1px solid #dcdcdc;
        padding-bottom: 12px;
      }}
      p {{
        margin: 0 0 10px 0;
        white-space: pre-wrap;
      }}
      ul, ol {{
        margin: 0 0 12px 24px;
      }}
      li {{
        margin-bottom: 6px;
      }}
    </style>
  </head>
  <body>
    <h1>{title}</h1>
    {body_html}
  </body>
</html>
"""


def export_note_to_pdf(
    pdf_path: Path,
    payload: PDFExportPayload,
    text_document_factory=None,
    printer_factory=None,
) -> Path:
    try:
        from PySide6 import QtGui, QtPrintSupport
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "Brakuje modułów Qt potrzebnych do eksportu PDF. "
            "Upewnij się, że PySide6 jest poprawnie zainstalowane."
        ) from error

    document_factory = text_document_factory or QtGui.QTextDocument
    effective_printer_factory = printer_factory or QtPrintSupport.QPrinter

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    document = document_factory()
    document.setHtml(build_note_html(payload))

    printer = effective_printer_factory(QtPrintSupport.QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QtPrintSupport.QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(pdf_path))
    margins = QtGui.QPageLayout.Margins(16, 16, 16, 16)
    printer.setPageMargins(margins, QtGui.QPageLayout.Unit.Millimeter)

    document.print(printer)
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
            paragraph_text = "<br />".join(escape(line) for line in paragraph_buffer)
            html_parts.append(f"<p>{paragraph_text}</p>")
            paragraph_buffer.clear()

    def flush_list() -> None:
        nonlocal current_list_type
        if list_buffer and current_list_type:
            tag = "ol" if current_list_type == "ordered" else "ul"
            items = "".join(f"<li>{escape(item)}</li>" for item in list_buffer)
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
