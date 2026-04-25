from __future__ import annotations

from typing import Iterable

from PySide6 import QtCore, QtWidgets

from app.models import Note
from app.storage import FileNoteRepository


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, repository: FileNoteRepository) -> None:
        super().__init__()
        self.repository = repository
        self.current_note: Note | None = None

        self.setWindowTitle("Notatki AI Desktop")
        self.resize(1100, 720)

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
        button_row.addWidget(self.new_button)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.refresh_button)
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
        self.note_list.itemSelectionChanged.connect(self._load_selected_note)

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
        self.statusBar().showMessage(f"Wczytano notatkę: {note.display_title}")

    def _save_current_note(self) -> None:
        if self.current_note is None:
            self.current_note = Note.create_empty()

        self.current_note.title = self.title_input.text().strip() or "Nowa notatka"
        self.current_note.content = self.content_input.toPlainText()

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

