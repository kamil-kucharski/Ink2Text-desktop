from pathlib import Path

from app.services import PDFExportPayload, build_note_html, export_note_to_pdf


class FakeTextDocument:
    def __init__(self) -> None:
        self.html = ""
        self.printed_with = None

    def setHtml(self, html: str) -> None:
        self.html = html

    def print(self, printer) -> None:
        self.printed_with = printer


class FakePrinter:
    class OutputFormat:
        PdfFormat = "pdf"

    class PrinterMode:
        HighResolution = "high"

    def __init__(self, mode) -> None:
        self.mode = mode
        self.output_format = None
        self.output_file = None
        self.margins = None

    def setOutputFormat(self, output_format) -> None:
        self.output_format = output_format

    def setOutputFileName(self, output_file: str) -> None:
        self.output_file = output_file

    def setPageMargins(self, margins, unit) -> None:
        self.margins = (margins, unit)


def test_build_note_html_formats_title_and_lists() -> None:
    html = build_note_html(
        PDFExportPayload(
            title="Moja notatka",
            content="Wstęp\n\n- punkt pierwszy\n- punkt drugi\n\n1. krok pierwszy",
        )
    )

    assert "<h1>Moja notatka</h1>" in html
    assert "<ul>" in html
    assert "<ol>" in html
    assert "punkt pierwszy" in html


def test_export_note_to_pdf_uses_document_and_printer_factories(tmp_path: Path) -> None:
    pdf_path = tmp_path / "wynik.pdf"

    returned_path = export_note_to_pdf(
        pdf_path,
        PDFExportPayload(
            title="Test",
            content="Treść notatki",
        ),
        text_document_factory=FakeTextDocument,
        printer_factory=FakePrinter,
    )

    assert returned_path == pdf_path
