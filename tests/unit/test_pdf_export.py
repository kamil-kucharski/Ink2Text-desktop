from pathlib import Path

from app.services import (
    PDFExportPayload,
    build_note_html,
    convert_note_content_to_editor_html,
    export_note_to_pdf,
)


class FakeTextDocument:
    def __init__(self) -> None:
        self.html = ""
        self.margin = None
        self.printed_with = None
        self.printed_with_legacy = None

    def setHtml(self, html: str) -> None:
        self.html = html

    def setDocumentMargin(self, margin: int) -> None:
        self.margin = margin

    def print_(self, printer) -> None:
        self.printed_with = printer

    def print(self, printer) -> None:
        self.printed_with_legacy = printer


class FakePdfWriter:
    def __init__(self, output_file: str) -> None:
        self.output_file = output_file
        self.resolution = None
        self.title = None
        self.creator = None
        self.margins = None

    def setResolution(self, resolution: int) -> None:
        self.resolution = resolution

    def setTitle(self, title: str) -> None:
        self.title = title

    def setCreator(self, creator: str) -> None:
        self.creator = creator

    def setPageMargins(self, margins, unit) -> None:
        self.margins = (margins, unit)


def test_build_note_html_formats_title_and_lists() -> None:
    html = build_note_html(
        PDFExportPayload(
            title="Moja notatka",
            content="### Wstęp\n#### Szczegóły\n\nTo jest **ważne** i mamy $\\to$.\n\n- punkt pierwszy\n- punkt drugi\n\n1. krok pierwszy",
        )
    )

    assert 'class="note-title">Moja notatka<' in html
    assert "<h3>Wstęp</h3>" in html
    assert "<h4>Szczegóły</h4>" in html
    assert "<strong>ważne</strong>" in html
    assert '<span class="math-inline">&rarr;</span>' in html
    assert "<ul>" in html
    assert "<ol>" in html
    assert "punkt pierwszy" in html


def test_build_note_html_hides_generic_note_title() -> None:
    html = build_note_html(
        PDFExportPayload(
            title="Notatka 1",
            content="Treść notatki",
        )
    )

    assert 'class="note-title"' not in html
    assert "<p>Treść notatki</p>" in html


def test_build_note_html_uses_rich_text_content_when_provided() -> None:
    html = build_note_html(
        PDFExportPayload(
            title="Elegancka notatka",
            content="To nie powinno być użyte",
            content_html="<html><body><p><strong>Gotowy</strong> fragment</p></body></html>",
        )
    )

    assert "<strong>Gotowy</strong> fragment" in html
    assert "To nie powinno być użyte" not in html


def test_convert_note_content_to_editor_html_replaces_heading_tags() -> None:
    editor_html = convert_note_content_to_editor_html("### Tytuł\n\nAkapit", "plain")

    assert "<h3>" not in editor_html
    assert "font-size: 15pt" in editor_html
    assert "Tytuł" in editor_html
    assert "Akapit" in editor_html


def test_export_note_to_pdf_uses_document_and_printer_factories(tmp_path: Path) -> None:
    pdf_path = tmp_path / "wynik.pdf"
    document = FakeTextDocument()

    returned_path = export_note_to_pdf(
        pdf_path,
        PDFExportPayload(
            title="Test",
            content="Treść notatki",
        ),
        text_document_factory=lambda: document,
        pdf_writer_factory=FakePdfWriter,
    )

    assert returned_path == pdf_path
    assert document.html
    assert document.margin == 24
    assert isinstance(document.printed_with, FakePdfWriter)
    assert document.printed_with_legacy is None
