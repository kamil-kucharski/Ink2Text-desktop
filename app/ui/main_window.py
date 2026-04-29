from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PySide6 import QtCore, QtGui, QtWidgets

from app.models import Note
from app.storage import FileNoteRepository
from app.ui.image_import import filter_supported_image_paths


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, repository: FileNoteRepository) -> None:
        super().__init__()
        self.repository = repository
        self.current_note: Note | None = None

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
        self.refresh_button = QtWidgets.QPushButton("Odśwież")
        self.import_images_button = QtWidgets.QPushButton("Importuj zdjęcia")
        button_row.addWidget(self.new_button)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.import_images_button)
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
        self.remove_image_button = QtWidgets.QPushButton("Usuń zaznaczone zdjęcie")
        attachments_layout.addWidget(attachments_header)
        attachments_layout.addStretch()
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
        self.save_button.clicked.connect(self._save_current_note)
        self.refresh_button.clicked.connect(self.refresh_notes)
        self.import_images_button.clicked.connect(self._import_images)
        self.remove_image_button.clicked.connect(self._remove_selected_image)
        self.note_list.itemSelectionChanged.connect(self._load_selected_note)
        self.image_list.itemSelectionChanged.connect(self._update_image_preview)

    def refresh_notes(self) -> None:
        self.note_list.clear()
        notes = self.repository.list_notes()
        self._populate_note_list(notes)
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
        self.title_input.setText(self.current_note.title)
        self.content_input.setPlainText(self.current_note.content)
        self._refresh_image_list()
        self.note_list.clearSelection()
        self.statusBar().showMessage("Utworzono nową notatkę")

    def _load_selected_note(self) -> None:
        selected_items = self.note_list.selectedItems()
        if not selected_items:
            return

        note_id = selected_items[0].data(QtCore.Qt.ItemDataRole.UserRole)
        if not note_id:
            return

        note = self.repository.get_note(note_id)
        self.current_note = note
        self.title_input.setText(note.title)
        self.content_input.setPlainText(note.content)
        self._refresh_image_list()
        self.statusBar().showMessage(f"Wczytano notatkę: {note.display_title}")

    def _save_current_note(self) -> None:
        if self.current_note is None:
            self.current_note = Note.create_empty()

        self._sync_form_to_current_note()
        saved_note = self.repository.save(self.current_note)
        self.refresh_notes()
        self._select_note(saved_note.id)
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
        self.refresh_notes()
        self._select_note(self.current_note.id)
        self.statusBar().showMessage("Usunięto zdjęcie z notatki")

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
        self.refresh_notes()
        self._select_note(self.current_note.id)

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
