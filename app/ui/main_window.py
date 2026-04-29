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
    convert_note_content_to_html,
    convert_note_content_to_editor_html,
    export_note_to_pdf,
)
from app.storage import FileNoteRepository
from app.ui.image_import import filter_supported_image_paths
from app.ui.i18n import translate
from app.ui.menu_select import MenuSelectButton
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
        self._updating_format_controls = False
        self.app_language = app_config.app_language if app_config.app_language in {"pl", "en"} else "pl"

        self.resize(1100, 720)
        self.setAcceptDrops(True)

        self._build_ui()
        self._apply_translations()
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
        self.language_button = MenuSelectButton()
        self.language_button.addItem("Polski", "pl")
        self.language_button.addItem("English", "en")
        self.language_button.setCurrentData(self.app_language)
        button_row.addWidget(self.new_button)
        button_row.addWidget(self.export_pdf_button)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.import_images_button)
        button_row.addWidget(self.transcribe_ai_button)
        button_row.addWidget(self.ai_settings_button)
        button_row.addWidget(self.language_button)
        button_row.addStretch()

        splitter = QtWidgets.QSplitter()
        splitter.setChildrenCollapsible(False)

        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        self.saved_notes_label = QtWidgets.QLabel()
        left_layout.addWidget(self.saved_notes_label)
        self.note_list = QtWidgets.QListWidget()
        left_layout.addWidget(self.note_list)

        right_panel = QtWidgets.QWidget()
        form_layout = QtWidgets.QVBoxLayout(right_panel)
        self.title_label = QtWidgets.QLabel()
        form_layout.addWidget(self.title_label)
        self.title_input = QtWidgets.QLineEdit()
        form_layout.addWidget(self.title_input)
        attachments_layout = QtWidgets.QHBoxLayout()
        self.attachments_header = QtWidgets.QLabel()
        self.move_image_earlier_button = QtWidgets.QPushButton("Wcześniej")
        self.move_image_later_button = QtWidgets.QPushButton("Później")
        self.remove_image_button = QtWidgets.QPushButton("Usuń zaznaczone zdjęcie")
        attachments_layout.addWidget(self.attachments_header)
        attachments_layout.addStretch()
        attachments_layout.addWidget(self.move_image_earlier_button)
        attachments_layout.addWidget(self.move_image_later_button)
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
        self.image_preview = QtWidgets.QLabel()
        self.image_preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMinimumHeight(220)
        self.image_preview.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.image_preview.setStyleSheet("background-color: #f4f4f4; color: #555;")
        image_splitter.addWidget(self.image_list)
        image_splitter.addWidget(self.image_preview)
        image_splitter.setStretchFactor(0, 1)
        image_splitter.setStretchFactor(1, 2)
        form_layout.addWidget(image_splitter)
        self.drag_hint = QtWidgets.QLabel()
        self.drag_hint.setStyleSheet("color: #666;")
        form_layout.addWidget(self.drag_hint)
        transcription_mode_layout = QtWidgets.QHBoxLayout()
        self.transcription_mode_label = QtWidgets.QLabel()
        transcription_mode_layout.addWidget(self.transcription_mode_label)
        self.transcription_mode_input = MenuSelectButton()
        self.transcription_mode_input.setMinimumWidth(220)
        transcription_mode_layout.addWidget(self.transcription_mode_input)
        transcription_mode_layout.addStretch()
        form_layout.addLayout(transcription_mode_layout)
        self._build_editor_toolbar()
        form_layout.addWidget(self.editor_toolbar)
        self.content_input = QtWidgets.QTextEdit()
        self.content_input.setAcceptRichText(True)
        self.content_input.setStyleSheet("background-color: white;")
        form_layout.addWidget(self.content_input, stretch=1)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        root_layout.addLayout(button_row)
        root_layout.addWidget(splitter, stretch=1)

        self.setCentralWidget(central_widget)
        self.statusBar().showMessage(self._tr("status_ready"))

        self.new_button.clicked.connect(self._create_new_note)
        self.export_pdf_button.clicked.connect(self._export_current_note_to_pdf)
        self.save_button.clicked.connect(self._save_current_note)
        self.refresh_button.clicked.connect(self.refresh_notes)
        self.import_images_button.clicked.connect(self._import_images)
        self.transcribe_ai_button.clicked.connect(self._transcribe_current_note_with_ai)
        self.ai_settings_button.clicked.connect(self._open_ai_settings)
        self.move_image_earlier_button.clicked.connect(lambda: self._move_selected_image(-1))
        self.move_image_later_button.clicked.connect(lambda: self._move_selected_image(1))
        self.remove_image_button.clicked.connect(self._remove_selected_image)
        self.note_list.itemSelectionChanged.connect(self._load_selected_note)
        self.image_list.itemSelectionChanged.connect(self._update_image_preview)
        self.language_button.currentDataChanged.connect(self._change_language)
        self.content_input.currentCharFormatChanged.connect(self._sync_format_controls)
        self.content_input.cursorPositionChanged.connect(self._sync_format_controls)

    def _build_editor_toolbar(self) -> None:
        toolbar = QtWidgets.QToolBar("Formatowanie")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QtCore.QSize(16, 16))
        self.editor_toolbar = toolbar

        self.bold_action = toolbar.addAction(self._build_toolbar_icon("bold"), "")
        self.bold_action.setCheckable(True)
        self.bold_action.setToolTip("Pogrubienie")

        self.italic_action = toolbar.addAction(self._build_toolbar_icon("italic"), "")
        self.italic_action.setCheckable(True)
        self.italic_action.setToolTip("Kursywa")

        self.underline_action = toolbar.addAction(self._build_toolbar_icon("underline"), "")
        self.underline_action.setCheckable(True)
        self.underline_action.setToolTip("Podkreślenie")

        toolbar.addSeparator()
        self.bulleted_list_action = toolbar.addAction(self._build_toolbar_icon("bulleted-list"), "")
        self.bulleted_list_action.setToolTip("Lista punktowana")
        self.numbered_list_action = toolbar.addAction(self._build_toolbar_icon("numbered-list"), "")
        self.numbered_list_action.setToolTip("Lista numerowana")

        toolbar.addSeparator()
        self.font_family_input = MenuSelectButton()
        self.font_family_input.setMinimumWidth(220)
        for family in QtGui.QFontDatabase.families():
            self.font_family_input.addItem(family, family)
        toolbar.addWidget(self.font_family_input)

        self.font_size_input = MenuSelectButton()
        self.font_size_input.setMinimumWidth(72)
        for size in ("10", "11", "12", "13", "14", "16", "18", "20", "24", "28", "32"):
            self.font_size_input.addItem(size)
        toolbar.addWidget(self.font_size_input)

        self.bold_action.triggered.connect(self._toggle_bold)
        self.italic_action.triggered.connect(self._toggle_italic)
        self.underline_action.triggered.connect(self._toggle_underline)
        self.bulleted_list_action.triggered.connect(
            lambda: self._insert_list(QtGui.QTextListFormat.Style.ListDisc)
        )
        self.numbered_list_action.triggered.connect(
            lambda: self._insert_list(QtGui.QTextListFormat.Style.ListDecimal)
        )
        self.font_family_input.currentTextChanged.connect(self._set_font_family)
        self.font_size_input.currentTextChanged.connect(self._set_font_size)

    def _apply_translations(self) -> None:
        self.setWindowTitle(self._tr("app_title"))
        self.new_button.setText(self._tr("button_new_note"))
        self.export_pdf_button.setText(self._tr("button_export_pdf"))
        self.save_button.setText(self._tr("button_save"))
        self.refresh_button.setText(self._tr("button_refresh"))
        self.import_images_button.setText(self._tr("button_import_images"))
        self.transcribe_ai_button.setText(self._tr("button_transcribe_ai"))
        self.ai_settings_button.setText(self._tr("button_ai_settings"))
        self.saved_notes_label.setText(self._tr("label_saved_notes"))
        self.title_label.setText(self._tr("label_title"))
        self.attachments_header.setText(self._tr("label_images"))
        self.move_image_earlier_button.setText(self._tr("button_move_earlier"))
        self.move_image_later_button.setText(self._tr("button_move_later"))
        self.remove_image_button.setText(self._tr("button_remove_selected_image"))
        self.drag_hint.setText(self._tr("label_drag_hint"))
        self.transcription_mode_label.setText(self._tr("label_ai_mode"))
        self.content_input.setPlaceholderText(self._tr("placeholder_note_content"))
        self.bold_action.setToolTip(self._tr("tooltip_bold"))
        self.italic_action.setToolTip(self._tr("tooltip_italic"))
        self.underline_action.setToolTip(self._tr("tooltip_underline"))
        self.bulleted_list_action.setToolTip(self._tr("tooltip_bulleted_list"))
        self.numbered_list_action.setToolTip(self._tr("tooltip_numbered_list"))
        self._rebuild_language_button()
        self._rebuild_transcription_mode_button()
        if not self.image_list.selectedItems() and self.image_preview.pixmap() is None:
            self.image_preview.setText(self._tr("label_no_image_selected"))

    def _rebuild_language_button(self) -> None:
        current_language = self.app_language
        self.language_button.blockSignals(True)
        self.language_button.clear()
        self.language_button.addItem(self._tr("lang_polish"), "pl")
        self.language_button.addItem(self._tr("lang_english"), "en")
        self.language_button.setCurrentData(current_language)
        self.language_button.blockSignals(False)

    def _rebuild_transcription_mode_button(self) -> None:
        current_mode = self.transcription_mode_input.currentData() or "faithful"
        self.transcription_mode_input.blockSignals(True)
        self.transcription_mode_input.clear()
        for mode in ("faithful", "formatted", "organized", "expanded"):
            self.transcription_mode_input.addItem(self._mode_label(mode), mode)
        self.transcription_mode_input.setCurrentData(current_mode)
        self.transcription_mode_input.blockSignals(False)

    def _change_language(self, language_code: object) -> None:
        if not isinstance(language_code, str) or language_code == self.app_language:
            return

        self.app_language = language_code
        self.app_config.app_language = language_code
        self._apply_translations()
        self.statusBar().showMessage(
            self._tr("status_language_changed", language=self._language_display_name(language_code))
        )
        try:
            save_app_config(
                self.app_config.config_path,
                gemini_api_key=self.app_config.gemini_api_key or "",
                gemini_model=self.app_config.gemini_model,
                app_language=self.app_language,
            )
        except OSError:
            pass

    def _language_display_name(self, language_code: str) -> str:
        return self._tr("lang_polish") if language_code == "pl" else self._tr("lang_english")

    def _mode_label(self, mode: str) -> str:
        return self._tr(f"mode_{mode}")

    def _tr(self, key: str, **kwargs) -> str:
        return translate(self.app_language, key, **kwargs)

    def _build_toolbar_icon(self, kind: str) -> QtGui.QIcon:
        pixmap = QtGui.QPixmap(18, 18)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        pen = QtGui.QPen(QtGui.QColor("#1f2937"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QtGui.QColor("#1f2937"))

        if kind == "bold":
            font = QtGui.QFont("DejaVu Sans", 11)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, "B")
        elif kind == "italic":
            font = QtGui.QFont("DejaVu Sans", 11)
            font.setItalic(True)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, "I")
        elif kind == "underline":
            font = QtGui.QFont("DejaVu Sans", 10)
            painter.setFont(font)
            painter.drawText(pixmap.rect().adjusted(0, -1, 0, 0), QtCore.Qt.AlignmentFlag.AlignCenter, "U")
            painter.drawLine(4, 14, 14, 14)
        elif kind == "bulleted-list":
            for y in (4, 9, 14):
                painter.drawEllipse(QtCore.QPointF(4, y), 1.3, 1.3)
                painter.drawLine(8, y, 15, y)
        elif kind == "numbered-list":
            font = QtGui.QFont("DejaVu Sans", 6)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QtCore.QRect(0, 0, 6, 6), QtCore.Qt.AlignmentFlag.AlignCenter, "1")
            painter.drawText(QtCore.QRect(0, 5, 6, 6), QtCore.Qt.AlignmentFlag.AlignCenter, "2")
            painter.drawText(QtCore.QRect(0, 10, 6, 6), QtCore.Qt.AlignmentFlag.AlignCenter, "3")
            for y in (4, 9, 14):
                painter.drawLine(8, y, 15, y)
        else:
            font = QtGui.QFont("DejaVu Sans", 9)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, "?")

        painter.end()
        return QtGui.QIcon(pixmap)

    def _merge_char_format(self, char_format: QtGui.QTextCharFormat) -> None:
        cursor = self.content_input.textCursor()
        if not cursor.hasSelection():
            cursor.select(QtGui.QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(char_format)
        self.content_input.mergeCurrentCharFormat(char_format)

    def _toggle_bold(self) -> None:
        char_format = QtGui.QTextCharFormat()
        weight = QtGui.QFont.Weight.Bold if self.bold_action.isChecked() else QtGui.QFont.Weight.Normal
        char_format.setFontWeight(weight)
        self._merge_char_format(char_format)

    def _toggle_italic(self) -> None:
        char_format = QtGui.QTextCharFormat()
        char_format.setFontItalic(self.italic_action.isChecked())
        self._merge_char_format(char_format)

    def _toggle_underline(self) -> None:
        char_format = QtGui.QTextCharFormat()
        char_format.setFontUnderline(self.underline_action.isChecked())
        self._merge_char_format(char_format)

    def _insert_list(self, list_style: QtGui.QTextListFormat.Style) -> None:
        cursor = self.content_input.textCursor()
        cursor.beginEditBlock()
        list_format = QtGui.QTextListFormat()
        current_list = cursor.currentList()
        if current_list is not None:
            list_format = current_list.format()
        else:
            block_format = cursor.blockFormat()
            list_format.setIndent(max(block_format.indent(), 1))
            cursor.setBlockFormat(block_format)
        list_format.setStyle(list_style)
        cursor.createList(list_format)
        cursor.endEditBlock()

    def _set_font_family(self, family_name: str) -> None:
        if self._updating_format_controls:
            return
        char_format = QtGui.QTextCharFormat()
        char_format.setFontFamily(family_name)
        self._merge_char_format(char_format)

    def _set_font_size(self, size_text: str) -> None:
        if self._updating_format_controls:
            return
        try:
            size = float(size_text)
        except ValueError:
            return
        if size <= 0:
            return
        char_format = QtGui.QTextCharFormat()
        char_format.setFontPointSize(size)
        self._merge_char_format(char_format)

    def _sync_format_controls(self) -> None:
        if not hasattr(self, "content_input"):
            return

        self._updating_format_controls = True
        char_format = self.content_input.currentCharFormat()
        font = char_format.font()
        self.bold_action.setChecked(font.bold())
        self.italic_action.setChecked(font.italic())
        self.underline_action.setChecked(font.underline())
        self.font_family_input.setCurrentText(font.family())
        point_size = char_format.fontPointSize() or self.content_input.fontPointSize() or 12
        self.font_size_input.setCurrentText(str(int(point_size)))
        self._updating_format_controls = False

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
        message = (
            self._tr("status_no_notes")
            if note_count == 0
            else self._tr("status_notes_found", count=note_count)
        )
        self.statusBar().showMessage(message)

    def _populate_note_list(self, notes: Iterable[Note]) -> None:
        for note in notes:
            item = QtWidgets.QListWidgetItem(note.display_title)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, note.id)
            item.setToolTip(note.updated_at.astimezone().strftime("%Y-%m-%d %H:%M"))
            self.note_list.addItem(item)

    def _create_new_note(self) -> None:
        self.current_note = Note.create_empty()
        self.current_note.title = self._tr("default_note_title")
        self._display_note(self.current_note)
        self.note_list.blockSignals(True)
        self.note_list.clearSelection()
        self.note_list.blockSignals(False)
        self.statusBar().showMessage(self._tr("status_new_note"))

    def _load_selected_note(self) -> None:
        selected_items = self.note_list.selectedItems()
        if not selected_items:
            return

        note_id = selected_items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        if not note_id:
            return

        note = self.repository.get_note(note_id)
        self._display_note(note)
        self.statusBar().showMessage(self._tr("status_loaded_note", title=note.display_title))

    def _save_current_note(self) -> None:
        if self.current_note is None:
            self.current_note = Note.create_empty()
            self.current_note.title = self._tr("default_note_title")

        self._sync_form_to_current_note()
        saved_note = self.repository.save(self.current_note)
        self.current_note = saved_note
        self.refresh_notes(selected_note_id=saved_note.id)
        self.statusBar().showMessage(self._tr("status_saved_note", title=saved_note.display_title))

    def _select_note(self, note_id: str) -> None:
        for row in range(self.note_list.count()):
            item = self.note_list.item(row)
            if item.data(QtCore.Qt.ItemDataRole.UserRole) == note_id:
                self.note_list.setCurrentItem(item)
                return

    def _import_images(self) -> None:
        selected_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            self._tr("dialog_choose_images"),
            "",
            self._tr("dialog_image_files"),
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
            self.statusBar().showMessage(self._tr("status_select_image_to_remove"))
            return

        relative_path = selected_items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        self.repository.remove_image(self.current_note, relative_path)
        self._refresh_image_list()
        self.refresh_notes(selected_note_id=self.current_note.id)
        self.statusBar().showMessage(self._tr("status_removed_image"))

    def _move_selected_image(self, direction: int) -> None:
        if self.current_note is None:
            return

        self._sync_form_to_current_note()
        selected_items = self.image_list.selectedItems()
        if not selected_items:
            self.statusBar().showMessage(self._tr("status_select_image_to_move"))
            return

        relative_path = selected_items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        moved = self.repository.move_image(self.current_note, relative_path, direction)
        if not moved:
            self.statusBar().showMessage(self._tr("status_image_cannot_move_more"))
            return

        self._refresh_image_list()
        self._select_image(relative_path)
        self.refresh_notes(selected_note_id=self.current_note.id)
        self.statusBar().showMessage(self._tr("status_changed_image_order"))

    def _prepare_images_for_ai(self) -> None:
        if self.current_note is None:
            return

        self._sync_form_to_current_note()
        if not self.current_note.image_paths:
            self.statusBar().showMessage(self._tr("status_add_images_before_prepare"))
            return

        try:
            prepared_images = self.image_preparation_service.prepare_note_images(
                self.current_note,
                self.repository,
            )
        except RuntimeError as error:
            QtWidgets.QMessageBox.warning(self, self._tr("dialog_missing_dependency"), str(error))
            self.statusBar().showMessage(self._tr("status_prepare_failed"))
            return

        if not prepared_images:
            self.statusBar().showMessage(self._tr("status_prepare_failed"))
            return

        output_dir = prepared_images[0].prepared_path.parent
        summary_lines = [
            self._tr("dialog_images_prepared_count", count=len(prepared_images)),
            self._tr("dialog_images_output_dir", path=output_dir),
        ]
        QtWidgets.QMessageBox.information(
            self,
            self._tr("dialog_images_ready"),
            "\n".join(summary_lines),
        )
        self.statusBar().showMessage(self._tr("status_prepared_images", count=len(prepared_images)))

    def _transcribe_current_note_with_ai(self) -> None:
        if self.current_note is None:
            return
        if self.ai_thread is not None:
            self.statusBar().showMessage(self._tr("status_ai_already_running"))
            return
        if self.app_config.load_error and not self.app_config.gemini_api_key:
            QtWidgets.QMessageBox.warning(self, self._tr("dialog_config_error"), self.app_config.load_error)
            self.statusBar().showMessage(self._tr("status_fix_ai_config"))
            return

        self._sync_form_to_current_note()
        if not self.current_note.image_paths:
            self.statusBar().showMessage(self._tr("status_add_images_before_ai"))
            return

        try:
            prepared_images = self.image_preparation_service.prepare_note_images(
                self.current_note,
                self.repository,
            )
        except RuntimeError as error:
            QtWidgets.QMessageBox.warning(self, self._tr("dialog_missing_dependency"), str(error))
            self.statusBar().showMessage(self._tr("status_prepare_ai_failed"))
            return

        prepared_paths = [image.prepared_path for image in prepared_images]
        if not prepared_paths:
            self.statusBar().showMessage(self._tr("status_prepare_ai_failed"))
            return

        transcription_mode = self.transcription_mode_input.currentData()
        self._set_ai_busy(True)
        self.statusBar().showMessage(self._tr("status_ai_processing"))

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
        dialog = AISettingsDialog(self.app_config, self.app_language, self)
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        try:
            save_app_config(
                self.app_config.config_path,
                gemini_api_key=dialog.api_key,
                gemini_model=dialog.model_name,
                app_language=self.app_language,
            )
        except OSError as error:
            QtWidgets.QMessageBox.warning(
                self,
                self._tr("dialog_save_settings_error"),
                f"{self._tr('dialog_save_settings_error')}: {error}",
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
            self._tr("dialog_saved_settings"),
            self._tr("dialog_saved_settings_message"),
        )
        self.statusBar().showMessage(
            self._tr("status_saved_ai_settings", model=self.app_config.gemini_model)
        )

    def _export_current_note_to_pdf(self) -> None:
        if self.current_note is None:
            self.current_note = Note.create_empty()
            self.current_note.title = self._tr("default_note_title")

        self._sync_form_to_current_note()
        title = self.current_note.title.strip() or self._tr("default_export_title")
        sanitized_title = (
            "".join(char if char.isalnum() else "_" for char in title).strip("_")
            or self._tr("default_export_title")
        )
        default_path = self.repository.base_dir / "exports" / f"{sanitized_title}.pdf"

        selected_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self._tr("dialog_export_pdf"),
            str(default_path),
            self._tr("dialog_pdf_files"),
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
                    content_html=(
                        self.current_note.content if self.current_note.content_format == "html" else None
                    ),
                ),
            )
        except RuntimeError as error:
            QtWidgets.QMessageBox.warning(self, self._tr("dialog_export_error"), str(error))
            self.statusBar().showMessage(self._tr("status_pdf_export_failed"))
            return
        except OSError as error:
            QtWidgets.QMessageBox.warning(
                self,
                self._tr("dialog_save_error"),
                f"{self._tr('dialog_save_error')}: {error}",
            )
            self.statusBar().showMessage(self._tr("status_pdf_save_failed"))
            return

        QtWidgets.QMessageBox.information(
            self,
            self._tr("dialog_export_finished"),
            self._tr("dialog_export_finished_message", path=pdf_path),
        )
        self.statusBar().showMessage(self._tr("status_pdf_exported", name=pdf_path.name))

    def _refresh_image_list(self) -> None:
        self.image_list.clear()
        self.image_preview.clear()
        self.image_preview.setText(self._tr("label_no_image_selected"))

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
            self.image_preview.setText(self._tr("label_no_image_selected"))
            return

        relative_path = selected_items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        image_path = self.repository.resolve_image_path(relative_path)
        pixmap = QtGui.QPixmap(str(image_path))

        if pixmap.isNull():
            self.image_preview.clear()
            self.image_preview.setText(self._tr("label_preview_load_failed"))
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

        self.current_note.title = self.title_input.text().strip() or self._tr("default_note_title")
        if self.content_input.toPlainText().strip():
            self.current_note.content = self.content_input.toHtml()
            self.current_note.content_format = "html"
        else:
            self.current_note.content = ""
            self.current_note.content_format = "html"

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if self._extract_image_paths_from_mime_data(event.mimeData()):
            event.acceptProposedAction()
            self.statusBar().showMessage(self._tr("status_drag_drop_images"))
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
            self.statusBar().showMessage(self._tr("status_drop_not_supported"))
            return

        event.acceptProposedAction()
        self._import_images_from_paths(image_paths)

    def _import_images_from_paths(self, selected_paths: list[str]) -> None:
        if self.current_note is None:
            self.current_note = Note.create_empty()
            self.current_note.title = self._tr("default_note_title")

        self._sync_form_to_current_note()
        filtered_paths = filter_supported_image_paths(selected_paths)
        if not filtered_paths:
            self.statusBar().showMessage(self._tr("status_no_supported_images"))
            return

        imported_paths = self.repository.import_images(self.current_note, filtered_paths)
        if not imported_paths:
            self.statusBar().showMessage(self._tr("status_import_failed"))
            return

        self._refresh_image_list()
        self._select_image(imported_paths[-1])
        self.statusBar().showMessage(self._tr("status_imported_images", count=len(imported_paths)))
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
        if note.content.strip():
            if note.content_format == "html":
                self.content_input.setHtml(convert_note_content_to_editor_html(note.content, "html"))
            else:
                self.content_input.setHtml(
                    convert_note_content_to_editor_html(note.content, note.content_format)
                )
        else:
            self.content_input.clear()
        self._refresh_image_list()
        self._sync_format_controls()

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
                self._tr("status_ai_result_unsupported")
            )
            return

        self._apply_transcription_result(result)
        mode_label = self._mode_label(result.transcription_mode)
        self.statusBar().showMessage(
            self._tr("status_ai_done", model=result.model_name, mode=mode_label)
        )

    @QtCore.Slot(str)
    def _handle_ai_transcription_failure(self, message: str) -> None:
        QtWidgets.QMessageBox.warning(self, self._tr("dialog_ai_error"), message)
        self.statusBar().showMessage(self._tr("status_ai_failed"))

    @QtCore.Slot()
    def _finish_ai_transcription(self) -> None:
        self._set_ai_busy(False)
        self.ai_worker = None
        self.ai_thread = None

    def _apply_transcription_result(self, result: TranscriptionResult) -> None:
        existing_text = self.content_input.toPlainText().strip()
        transcription_text = result.text.strip()
        transcription_html = convert_note_content_to_editor_html(transcription_text, "plain")

        if existing_text:
            decision = self._ask_how_to_apply_transcription()
            if decision == "cancel":
                self.statusBar().showMessage(self._tr("status_ai_insert_cancelled"))
                return
            if decision == "append":
                cursor = self.content_input.textCursor()
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.End)
                cursor.insertHtml("<p><br /></p>")
                cursor.insertHtml(transcription_html)
                self.content_input.setTextCursor(cursor)
                return

        self.content_input.setHtml(transcription_html)

    def _ask_how_to_apply_transcription(self) -> str:
        message_box = QtWidgets.QMessageBox(self)
        message_box.setWindowTitle(self._tr("dialog_existing_content_title"))
        message_box.setText(self._tr("dialog_existing_content_text"))
        replace_button = message_box.addButton(
            self._tr("dialog_replace_content"),
            QtWidgets.QMessageBox.ButtonRole.AcceptRole,
        )
        append_button = message_box.addButton(
            self._tr("dialog_append_content"),
            QtWidgets.QMessageBox.ButtonRole.ActionRole,
        )
        cancel_button = message_box.addButton(self._tr("dialog_cancel"), QtWidgets.QMessageBox.ButtonRole.RejectRole)
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
        self.import_images_button.setDisabled(is_busy)
