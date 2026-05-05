from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6 import QtCore, QtGui, QtWidgets


class PDFPreviewDialog(QtWidgets.QDialog):
    def __init__(
        self,
        pdf_path: Path,
        title: str,
        parent: QtWidgets.QWidget | None = None,
        translator: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._tr = translator or self._fallback_translate
        try:
            from PySide6 import QtPdf, QtPdfWidgets
        except ModuleNotFoundError as error:
            raise RuntimeError(self._tr("dialog_pdf_dependency_error")) from error

        self.pdf_path = pdf_path
        self.setWindowTitle(title)
        self.resize(1100, 780)
        self._zoom_factor = 0.82

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        toolbar = QtWidgets.QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)
        toolbar.addStretch()
        self.zoom_out_button = QtWidgets.QPushButton("−")
        self.zoom_out_button.setObjectName("IconButton")
        self.zoom_label = QtWidgets.QLabel()
        self.zoom_label.setObjectName("StatusMeta")
        self.zoom_label.setMinimumWidth(54)
        self.zoom_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.zoom_in_button = QtWidgets.QPushButton("+")
        self.zoom_in_button.setObjectName("IconButton")
        self.fit_width_button = QtWidgets.QPushButton(self._tr("dialog_fit_width"))
        self.fit_width_button.setObjectName("DialogCloseButton")
        toolbar.addWidget(self.zoom_out_button)
        toolbar.addWidget(self.zoom_label)
        toolbar.addWidget(self.zoom_in_button)
        toolbar.addWidget(self.fit_width_button)
        layout.addLayout(toolbar)

        self.pdf_document = QtPdf.QPdfDocument(self)
        load_error = self.pdf_document.load(str(pdf_path))
        if load_error != QtPdf.QPdfDocument.Error.None_:
            raise RuntimeError(self._tr("dialog_pdf_preview_load_failed"))

        self.pdf_view = QtPdfWidgets.QPdfView()
        self.pdf_view.setObjectName("PDFPreviewView")
        self.pdf_view.setDocument(self.pdf_document)
        self.pdf_view.setPageMode(QtPdfWidgets.QPdfView.PageMode.MultiPage)
        self.pdf_view.setZoomMode(QtPdfWidgets.QPdfView.ZoomMode.Custom)
        self.pdf_view.setZoomFactor(self._zoom_factor)
        self.pdf_view.viewport().installEventFilter(self)
        layout.addWidget(self.pdf_view, stretch=1)

        self.zoom_out_button.clicked.connect(lambda: self._change_zoom(-0.10))
        self.zoom_in_button.clicked.connect(lambda: self._change_zoom(0.10))
        self.fit_width_button.clicked.connect(self._fit_to_width)
        self._update_zoom_label()

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if watched is self.pdf_view.viewport() and event.type() == QtCore.QEvent.Type.Wheel:
            if event.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
                wheel_event = event
                delta = 0.08 if wheel_event.angleDelta().y() > 0 else -0.08
                self._change_zoom(delta)
                return True
        return super().eventFilter(watched, event)

    def _change_zoom(self, delta: float) -> None:
        self._set_zoom(self.pdf_view.zoomFactor() + delta)

    def _set_zoom(self, zoom_factor: float) -> None:
        self._zoom_factor = max(0.35, min(2.4, zoom_factor))
        self.pdf_view.setZoomMode(self.pdf_view.ZoomMode.Custom)
        self.pdf_view.setZoomFactor(self._zoom_factor)
        self._update_zoom_label()

    def _fit_to_width(self) -> None:
        self.pdf_view.setZoomMode(self.pdf_view.ZoomMode.FitToWidth)
        self._zoom_factor = self.pdf_view.zoomFactor()
        self.zoom_label.setText(self._tr("dialog_auto_zoom"))

    def _update_zoom_label(self) -> None:
        self.zoom_label.setText(f"{round(self._zoom_factor * 100)}%")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.pdf_document.close()
        try:
            self.pdf_path.unlink(missing_ok=True)
        except OSError:
            pass
        super().closeEvent(event)

    def _fallback_translate(self, key: str) -> str:
        fallback = {
            "dialog_pdf_dependency_error": (
                "Brakuje modułów Qt potrzebnych do podglądu PDF. "
                "Upewnij się, że PySide6 jest poprawnie zainstalowane."
            ),
            "dialog_pdf_preview_load_failed": "Nie udało się wczytać wygenerowanego podglądu PDF.",
            "dialog_fit_width": "Dopasuj",
            "dialog_auto_zoom": "Auto",
        }
        return fallback.get(key, key)
