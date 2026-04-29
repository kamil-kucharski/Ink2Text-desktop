from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PySide6 import QtCore, QtGui, QtWidgets

from app.config import AppConfig, load_app_config, save_app_config
from app.models import Note
from app.services import (
    AIProvider,
    AIProviderError,
    GeminiAIProvider,
    ImagePreparationService,
    PDFExportPayload,
    TRANSCRIPTION_MODE_LABELS,
    TranscriptionResult,
    export_note_to_pdf,
)
from app.storage import FileNoteRepository
from app.ui.image_import import filter_supported_image_paths
from app.ui.settings_dialog import AISettingsDialog


class AITranscriptionWorker(QtCore.QObject):
    succeeded = QtCore.Signal(object)
    failed = QtCore.Signal(str)
    finished = QtCore.Signal()

    def __init__(
        self,
        ai_provider: AIProvider,
        image_paths: list[Path],
        transcription_mode: str,
    ) -> None:
        super().__init__()
        self.ai_provider = ai_provider
        self.image_paths = image_paths
        self.transcription_mode = transcription_mode

    @QtCore.Slot()
    def run(self) -> None:
        try:
            result = self.ai_provider.transcribe_images(
                self.image_paths,
                transcription_mode=self.transcription_mode,
            )
            self.succeeded.emit(result)
        except AIProviderError as error:
            self.failed.emit(str(error))
        except Exception as error:  # pragma: no cover - osłona dla nieprzewidzianych błędów
            self.failed.emit(f"Wystąpił nieoczekiwany błąd podczas przetwarzania AI: {error}")
        finally:
            self.finished.emit()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(
        self,
        repository: FileNoteRepository,
        image_preparation_service: ImagePreparationService,
        ai_provider: AIProvider,
        app_config: AppConfig,
    ) -> None:
        super().__init__()
        self.repository = repository
        self.image_preparation_service = image_preparation_service
        self.ai_provider = ai_provider
        self.app_config = app_config
        self.current_note: Note | None = None
        self.ai_thread: QtCore.QThread | None = None
        self.ai_worker: AITranscriptionWorker | None = None

        self.setWindowTitle("Notatki AI Desktop")
        self.resize(1100, 720)
        self.setAcceptDrops(True)

        self._build_ui()
        self.refresh_notes()
        self._create_new_note()

    def _build_ui(self) -> None:
        central_widget = QtWidgets.QWidget()
        root_layout = QtWidgets.QVBoxLayout(central_widget)

        button_row = QtWidgets.QHBoxLayout()
        self.new_button = QtWidgets.QPushButton("Nowa notatka")
        self.save_button = QtWidgets.QPushButton("Zapisz")
        self.export_pdf_button = QtWidgets.QPushButton("Eksportuj PDF")
        self.refresh_button = QtWidgets.QPushButton("Odśwież")
        self.import_images_button = QtWidgets.QPushButton("Importuj zdjęcia")
        self.transcribe_ai_button = QtWidgets.QPushButton("Przetwórz przez AI")
        self.ai_settings_button = QtWidgets.QPushButton("Ustawienia AI")
        button_row.addWidget(self.new_button)
        button_row.addWidget(self.export_pdf_button)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.import_images_button)
        button_row.addWidget(self.transcribe_ai_button)
        button_row.addWidget(self.ai_settings_button)
        button_row.addStretch()

        splitter = QtWidgets.QSplitter()
        splitter.setChildrenCollapsible(False)

        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.addWidget(QtWidgets.QLabel("Zapisane notatki"))
        self.note_list = QtWidgets.QListWidget()
        left_layout.addWidget(self.note_list)

        right_panel = QtWidgets.QWidget()
        form_layout = QtWidgets.QVBoxLayout(right_panel)
        form_layout.addWidget(QtWidgets.QLabel("Tytuł"))
        self.title_input = QtWidgets.QLineEdit()
        form_layout.addWidget(self.title_input)
        attachments_layout = QtWidgets.QHBoxLayout()
        attachments_header = QtWidgets.QLabel("Zdjęcia")
        self.move_image_earlier_button = QtWidgets.QPushButton("Wcześniej")
        self.move_image_later_button = QtWidgets.QPushButton("Później")
        self.prepare_images_button = QtWidgets.QPushButton("Przygotuj do AI")
        self.remove_image_button = QtWidgets.QPushButton("Usuń zaznaczone zdjęcie")
        attachments_layout.addWidget(attachments_header)
        attachments_layout.addStretch()
        attachments_layout.addWidget(self.move_image_earlier_button)
        attachments_layout.addWidget(self.move_image_later_button)
        attachments_layout.addWidget(self.prepare_images_button)
        attachments_layout.addWidget(self.remove_image_button)
        form_layout.addLayout(attachments_layout)
        image_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        image_splitter.setChildrenCollapsible(False)
        self.image_list = QtWidgets.QListWidget()
        self.image_list.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        self.image_list.setFlow(QtWidgets.QListView.Flow.LeftToRight)
        self.image_list.setWrapping(True)
        self.image_list.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.image_list.setMovement(QtWidgets.QListView.Movement.Static)
        self.image_list.setIconSize(QtCore.QSize(96, 96))
        self.image_list.setGridSize(QtCore.QSize(132, 132))
        self.image_list.setSpacing(10)
        self.image_preview = QtWidgets.QLabel("Brak wybranego zdjęcia")
        self.image_preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMinimumHeight(220)
        self.image_preview.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.image_preview.setStyleSheet("background-color: #f4f4f4; color: #555;")
        image_splitter.addWidget(self.image_list)
        image_splitter.addWidget(self.image_preview)
        image_splitter.setStretchFactor(0, 1)
        image_splitter.setStretchFactor(1, 2)
        form_layout.addWidget(image_splitter)
        drag_hint = QtWidgets.QLabel("Możesz też przeciągnąć zdjęcia do okna aplikacji.")
        drag_hint.setStyleSheet("color: #666;")
        form_layout.addWidget(drag_hint)
        transcription_mode_layout = QtWidgets.QHBoxLayout()
        transcription_mode_layout.addWidget(QtWidgets.QLabel("Tryb AI"))
        self.transcription_mode_input = QtWidgets.QComboBox()
        self.transcription_mode_input.addItem(TRANSCRIPTION_MODE_LABELS["faithful"], "faithful")
        self.transcription_mode_input.addItem(TRANSCRIPTION_MODE_LABELS["structured"], "structured")
        self.transcription_mode_input.addItem(TRANSCRIPTION_MODE_LABELS["polished"], "polished")
        transcription_mode_layout.addWidget(self.transcription_mode_input)
        transcription_mode_layout.addStretch()
        form_layout.addLayout(transcription_mode_layout)
        form_layout.addWidget(QtWidgets.QLabel("Treść"))
        self.content_input = QtWidgets.QPlainTextEdit()
        self.content_input.setPlaceholderText("Tutaj pojawi się treść notatki.")
        form_layout.addWidget(self.content_input, stretch=1)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        root_layout.addLayout(button_row)
        root_layout.addWidget(splitter, stretch=1)

        self.setCentralWidget(central_widget)
        self.statusBar().showMessage("Gotowe")

        self.new_button.clicked.connect(self._create_new_note)
        self.export_pdf_button.clicked.connect(self._export_current_note_to_pdf)
        self.save_button.clicked.connect(self._save_current_note)
        self.refresh_button.clicked.connect(self.refresh_notes)
        self.import_images_button.clicked.connect(self._import_images)
        self.transcribe_ai_button.clicked.connect(self._transcribe_current_note_with_ai)
        self.ai_settings_button.clicked.connect(self._open_ai_settings)
        self.move_image_earlier_button.clicked.connect(lambda: self._move_selected_image(-1))
        self.move_image_later_button.clicked.connect(lambda: self._move_selected_image(1))
        self.prepare_images_button.clicked.connect(self._prepare_images_for_ai)
        self.remove_image_button.clicked.connect(self._remove_selected_image)
        self.note_list.itemSelectionChanged.connect(self._load_selected_note)
        self.image_list.itemSelectionChanged.connect(self._update_image_preview)

    def refresh_notes(self, selected_note_id: str | None = None) -> None:
        if selected_note_id is None:
            selected_items = self.note_list.selectedItems()
            if selected_items:
                selected_note_id = selected_items[0].data(QtCore.Qt.ItemDataRole.UserRole)
            elif self.current_note is not None:
                selected_note_id = self.current_note.id

        self.note_list.blockSignals(True)
        self.note_list.clear()
        notes = self.repository.list_notes()
        self._populate_note_list(notes)
        if selected_note_id is not None:
            self._select_note(selected_note_id)
        self.note_list.blockSignals(False)

        if selected_note_id is not None and self._has_note_item(selected_note_id):
            note = self.repository.get_note(selected_note_id)
            self._display_note(note)

        note_count = len(notes)
        message = "Brak zapisanych notatek" if note_count == 0 else f"Znaleziono notatek: {note_count}"
        self.statusBar().showMessage(message)

    def _populate_note_list(self, notes: Iterable[Note]) -> None:
        for note in notes:
            item = QtWidgets.QListWidgetItem(note.display_title)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, note.id)
            item.setToolTip(note.updated_at.astimezone().strftime("%Y-%m-%d %H:%M"))
            self.note_list.addItem(item)

    def _create_new_note(self) -> None:
        self.current_note = Note.create_empty()
        self._display_note(self.current_note)
        self.note_list.blockSignals(True)
        self.note_list.clearSelection()
        self.note_list.blockSignals(False)
        self.statusBar().showMessage("Utworzono nową notatkę")

    def _load_selected_note(self) -> None:
        selected_items = self.note_list.selectedItems()
        if not selected_items:
            return

        note_id = selected_items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        if not note_id:
            return

        note = self.repository.get_note(note_id)
        self._display_note(note)
        self.statusBar().showMessage(f"Wczytano notatkę: {note.display_title}")

    def _save_current_note(self) -> None:
        if self.current_note is None:
            self.current_note = Note.create_empty()

        self._sync_form_to_current_note()
        saved_note = self.repository.save(self.current_note)
        self.current_note = saved_note
        self.refresh_notes(selected_note_id=saved_note.id)
        self.statusBar().showMessage(f"Zapisano notatkę: {saved_note.display_title}")

    def _select_note(self, note_id: str) -> None:
        for row in range(self.note_list.count()):
            item = self.note_list.item(row)
            if item.data(QtCore.Qt.ItemDataRole.UserRole) == note_id:
                self.note_list.setCurrentItem(item)
                return

    def _import_images(self) -> None:
        selected_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Wybierz zdjęcia notatki",
            "",
            "Pliki graficzne (*.png *.jpg *.jpeg *.bmp *.gif *.webp)",
        )
        if not selected_paths:
            return

        self._import_images_from_paths(selected_paths)

    def _remove_selected_image(self) -> None:
        if self.current_note is None:
            return

        self._sync_form_to_current_note()

        selected_items = self.image_list.selectedItems()
        if not selected_items:
            self.statusBar().showMessage("Najpierw zaznacz zdjęcie do usunięcia")
            return

        relative_path = selected_items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        self.repository.remove_image(self.current_note, relative_path)
        self._refresh_image_list()
        self.refresh_notes(selected_note_id=self.current_note.id)
        self.statusBar().showMessage("Usunięto zdjęcie z notatki")

    def _move_selected_image(self, direction: int) -> None:
        if self.current_note is None:
            return

        self._sync_form_to_current_note()
        selected_items = self.image_list.selectedItems()
        if not selected_items:
            self.statusBar().showMessage("Najpierw zaznacz zdjęcie do przesunięcia")
            return

        relative_path = selected_items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        moved = self.repository.move_image(self.current_note, relative_path, direction)
        if not moved:
            self.statusBar().showMessage("Tego zdjęcia nie da się już bardziej przesunąć")
            return

        self._refresh_image_list()
        self._select_image(relative_path)
        self.refresh_notes(selected_note_id=self.current_note.id)
        self.statusBar().showMessage("Zmieniono kolejność zdjęć")

    def _prepare_images_for_ai(self) -> None:
        if self.current_note is None:
            return

        self._sync_form_to_current_note()
        if not self.current_note.image_paths:
            self.statusBar().showMessage("Dodaj zdjęcia, zanim przygotujesz je do AI")
            return

        try:
            prepared_images = self.image_preparation_service.prepare_note_images(
                self.current_note,
                self.repository,
            )
        except RuntimeError as error:
            QtWidgets.QMessageBox.warning(self, "Brak zależności", str(error))
            self.statusBar().showMessage("Nie udało się przygotować zdjęć")
            return

        if not prepared_images:
            self.statusBar().showMessage("Nie udało się przygotować zdjęć")
            return

        output_dir = prepared_images[0].prepared_path.parent
        summary_lines = [
            f"Przygotowano zdjęć: {len(prepared_images)}",
            f"Katalog wyjściowy: {output_dir}",
        ]
        QtWidgets.QMessageBox.information(
            self,
            "Zdjęcia gotowe do AI",
            "\n".join(summary_lines),
        )
        self.statusBar().showMessage(f"Przygotowano zdjęć do AI: {len(prepared_images)}")

    def _transcribe_current_note_with_ai(self) -> None:
        if self.current_note is None:
            return
        if self.ai_thread is not None:
            self.statusBar().showMessage("Przetwarzanie AI już trwa")
            return
        if self.app_config.load_error and not self.app_config.gemini_api_key:
            QtWidgets.QMessageBox.warning(self, "Błąd konfiguracji", self.app_config.load_error)
            self.statusBar().showMessage("Popraw konfigurację AI i spróbuj ponownie")
            return

        self._sync_form_to_current_note()
        if not self.current_note.image_paths:
            self.statusBar().showMessage("Dodaj zdjęcia przed uruchomieniem AI")
            return

        try:
            prepared_images = self.image_preparation_service.prepare_note_images(
                self.current_note,
                self.repository,
            )
        except RuntimeError as error:
            QtWidgets.QMessageBox.warning(self, "Brak zależności", str(error))
            self.statusBar().showMessage("Nie udało się przygotować zdjęć do AI")
            return

        prepared_paths = [image.prepared_path for image in prepared_images]
        if not prepared_paths:
            self.statusBar().showMessage("Nie udało się przygotować zdjęć do AI")
            return

        transcription_mode = self.transcription_mode_input.currentData()
        self._set_ai_busy(True)
        self.statusBar().showMessage("Trwa przetwarzanie notatki przez AI...")

        self.ai_thread = QtCore.QThread(self)
        self.ai_worker = AITranscriptionWorker(
            self.ai_provider,
            prepared_paths,
            transcription_mode=transcription_mode,
        )
        self.ai_worker.moveToThread(self.ai_thread)

        self.ai_thread.started.connect(self.ai_worker.run)
        self.ai_worker.succeeded.connect(self._handle_ai_transcription_success)
        self.ai_worker.failed.connect(self._handle_ai_transcription_failure)
        self.ai_worker.finished.connect(self.ai_thread.quit)
        self.ai_worker.finished.connect(self.ai_worker.deleteLater)
        self.ai_thread.finished.connect(self.ai_thread.deleteLater)
        self.ai_thread.finished.connect(self._finish_ai_transcription)
        self.ai_thread.start()

    def _open_ai_settings(self) -> None:
        dialog = AISettingsDialog(self.app_config, self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        try:
            save_app_config(
                self.app_config.config_path,
                gemini_api_key=dialog.api_key,
                gemini_model=dialog.model_name,
            )
        except OSError as error:
            QtWidgets.QMessageBox.warning(
                self,
                "Błąd zapisu ustawień",
                f"Nie udało się zapisać ustawień AI: {error}",
            )
            return

        self.app_config = load_app_config(base_dir=self.repository.base_dir)
        self.ai_provider = GeminiAIProvider(
            api_key=self.app_config.gemini_api_key,
            model_name=self.app_config.gemini_model,
            config_path=self.app_config.config_path,
        )
        QtWidgets.QMessageBox.information(
            self,
            "Ustawienia zapisane",
            "Zapisano ustawienia AI. Nowe wartości będą używane od razu.",
        )
        self.statusBar().showMessage(f"Zapisano ustawienia AI dla modelu {self.app_config.gemini_model}")

    def _export_current_note_to_pdf(self) -> None:
        if self.current_note is None:
            self.current_note = Note.create_empty()

        self._sync_form_to_current_note()
        title = self.current_note.title.strip() or "notatka"
        sanitized_title = "".join(char if char.isalnum() else "_" for char in title).strip("_") or "notatka"
        default_path = self.repository.base_dir / "exports" / f"{sanitized_title}.pdf"

        selected_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Eksportuj notatkę do PDF",
            str(default_path),
            "Pliki PDF (*.pdf)",
        )
        if not selected_path:
            return

        pdf_path = Path(selected_path)
        if pdf_path.suffix.lower() != ".pdf":
            pdf_path = pdf_path.with_suffix(".pdf")

        try:
            export_note_to_pdf(
                pdf_path,
                PDFExportPayload(
                    title=self.current_note.title,
                    content=self.current_note.content,
                ),
            )
        except RuntimeError as error:
            QtWidgets.QMessageBox.warning(self, "Błąd eksportu", str(error))
            self.statusBar().showMessage("Nie udało się wyeksportować notatki do PDF")
            return
        except OSError as error:
            QtWidgets.QMessageBox.warning(
                self,
                "Błąd zapisu",
                f"Nie udało się zapisać pliku PDF: {error}",
            )
            self.statusBar().showMessage("Nie udało się zapisać pliku PDF")
            return

        QtWidgets.QMessageBox.information(
            self,
            "Eksport zakończony",
            f"Wyeksportowano notatkę do pliku:\n{pdf_path}",
        )
        self.statusBar().showMessage(f"Wyeksportowano PDF: {pdf_path.name}")

    def _refresh_image_list(self) -> None:
        self.image_list.clear()
        self.image_preview.clear()
        self.image_preview.setText("Brak wybranego zdjęcia")

        if self.current_note is None:
            return

        for relative_path in self.current_note.image_paths:
            image_path = self.repository.resolve_image_path(relative_path)
            item = QtWidgets.QListWidgetItem(self._build_image_icon(image_path), Path(relative_path).name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, relative_path)
            item.setToolTip(relative_path)
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.image_list.addItem(item)

        if self.image_list.count() > 0:
            self.image_list.setCurrentRow(0)

    def _update_image_preview(self) -> None:
        selected_items = self.image_list.selectedItems()
        if not selected_items:
            self.image_preview.clear()
            self.image_preview.setText("Brak wybranego zdjęcia")
            return

        relative_path = selected_items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        image_path = self.repository.resolve_image_path(relative_path)
        pixmap = QtGui.QPixmap(str(image_path))

        if pixmap.isNull():
            self.image_preview.clear()
            self.image_preview.setText("Nie udało się wczytać podglądu")
            return

        scaled = pixmap.scaled(
            self.image_preview.size(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        self.image_preview.setPixmap(scaled)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if self.image_preview.pixmap() is not None:
            self._update_image_preview()

    def _select_image(self, relative_path: str) -> None:
        for row in range(self.image_list.count()):
            item = self.image_list.item(row)
            if item.data(QtCore.Qt.ItemDataRole.UserRole) == relative_path:
                self.image_list.setCurrentItem(item)
                return

    def _sync_form_to_current_note(self) -> None:
        if self.current_note is None:
            return

        self.current_note.title = self.title_input.text().strip() or "Nowa notatka"
        self.current_note.content = self.content_input.toPlainText()

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if self._extract_image_paths_from_mime_data(event.mimeData()):
            event.acceptProposedAction()
            self.statusBar().showMessage("Upuść zdjęcia, aby dodać je do notatki")
            return

        event.ignore()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:
        if self._extract_image_paths_from_mime_data(event.mimeData()):
            event.acceptProposedAction()
            return

        event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        image_paths = self._extract_image_paths_from_mime_data(event.mimeData())
        if not image_paths:
            event.ignore()
            self.statusBar().showMessage("Upuszczone pliki nie są obsługiwanymi obrazami")
            return

        event.acceptProposedAction()
        self._import_images_from_paths(image_paths)

    def _import_images_from_paths(self, selected_paths: list[str]) -> None:
        if self.current_note is None:
            self.current_note = Note.create_empty()

        self._sync_form_to_current_note()
        filtered_paths = filter_supported_image_paths(selected_paths)
        if not filtered_paths:
            self.statusBar().showMessage("Nie znaleziono obsługiwanych plików graficznych")
            return

        imported_paths = self.repository.import_images(self.current_note, filtered_paths)
        if not imported_paths:
            self.statusBar().showMessage("Nie udało się zaimportować zdjęć")
            return

        self._refresh_image_list()
        self._select_image(imported_paths[-1])
        self.statusBar().showMessage(f"Zaimportowano zdjęć: {len(imported_paths)}")
        self.refresh_notes(selected_note_id=self.current_note.id)

    def _extract_image_paths_from_mime_data(self, mime_data: QtCore.QMimeData) -> list[str]:
        if not mime_data.hasUrls():
            return []

        local_paths = [url.toLocalFile() for url in mime_data.urls() if url.isLocalFile()]
        return filter_supported_image_paths(local_paths)

    def _build_image_icon(self, image_path: Path) -> QtGui.QIcon:
        pixmap = QtGui.QPixmap(str(image_path))
        if pixmap.isNull():
            return self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon)

        thumbnail = pixmap.scaled(
            self.image_list.iconSize(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        return QtGui.QIcon(thumbnail)

    def _display_note(self, note: Note) -> None:
        self.current_note = note
        self.title_input.setText(note.title)
        self.content_input.setPlainText(note.content)
        self._refresh_image_list()

    def _has_note_item(self, note_id: str) -> bool:
        for row in range(self.note_list.count()):
            item = self.note_list.item(row)
            if item.data(QtCore.Qt.ItemDataRole.UserRole) == note_id:
                return True
        return False

    @QtCore.Slot(object)
    def _handle_ai_transcription_success(self, result: object) -> None:
        if not isinstance(result, TranscriptionResult):
            self._handle_ai_transcription_failure(
                "Model zwrócił odpowiedź w nieobsługiwanym formacie."
            )
            return

        self._apply_transcription_result(result)
        mode_label = TRANSCRIPTION_MODE_LABELS.get(result.transcription_mode, result.transcription_mode)
        self.statusBar().showMessage(
            f"Notatka została przepisana przez model {result.model_name} w trybie: {mode_label}"
        )

    @QtCore.Slot(str)
    def _handle_ai_transcription_failure(self, message: str) -> None:
        QtWidgets.QMessageBox.warning(self, "Błąd AI", message)
        self.statusBar().showMessage("Nie udało się przetworzyć notatki przez AI")

    @QtCore.Slot()
    def _finish_ai_transcription(self) -> None:
        self._set_ai_busy(False)
        self.ai_worker = None
        self.ai_thread = None

    def _apply_transcription_result(self, result: TranscriptionResult) -> None:
        existing_text = self.content_input.toPlainText().strip()
        transcription_text = result.text.strip()

        if existing_text:
            decision = self._ask_how_to_apply_transcription()
            if decision == "cancel":
                self.statusBar().showMessage("Anulowano wstawianie wyniku AI")
                return
            if decision == "append":
                merged_text = f"{self.content_input.toPlainText().rstrip()}\n\n{transcription_text}"
                self.content_input.setPlainText(merged_text)
                return

        self.content_input.setPlainText(transcription_text)

    def _ask_how_to_apply_transcription(self) -> str:
        message_box = QtWidgets.QMessageBox(self)
        message_box.setWindowTitle("Treść już istnieje")
        message_box.setText("Notatka ma już treść. Jak chcesz wstawić wynik AI?")
        replace_button = message_box.addButton("Zastąp treść", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
        append_button = message_box.addButton("Dopisz na końcu", QtWidgets.QMessageBox.ButtonRole.ActionRole)
        cancel_button = message_box.addButton(QtWidgets.QMessageBox.StandardButton.Cancel)
        message_box.exec()

        clicked_button = message_box.clickedButton()
        if clicked_button == replace_button:
            return "replace"
        if clicked_button == append_button:
            return "append"
        if clicked_button == cancel_button:
            return "cancel"
        return "cancel"

    def _set_ai_busy(self, is_busy: bool) -> None:
        self.transcribe_ai_button.setDisabled(is_busy)
        self.prepare_images_button.setDisabled(is_busy)
        self.import_images_button.setDisabled(is_busy)
