from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from app.models import Note
from app.storage import FileNoteRepository
from app.ui.icons import build_simple_icon


class NoteListItemWidget(QtWidgets.QFrame):
    selectedRequested = QtCore.Signal(str)
    trashRequested = QtCore.Signal(str)

    def __init__(
        self,
        note: Note,
        updated_label: str,
        parent: QtWidgets.QWidget | None = None,
        trash_tooltip: str = "Przenieś do kosza",
    ) -> None:
        super().__init__(parent)
        self.note_id = note.id
        self.setObjectName("NoteItemWidget")
        self.setMouseTracking(True)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(8)

        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        self.title_label = QtWidgets.QLabel(note.display_title)
        self.title_label.setObjectName("NoteItemTitle")
        self.date_label = QtWidgets.QLabel(updated_label)
        self.date_label.setObjectName("NoteItemMeta")
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.date_label)

        self.trash_button = QtWidgets.QPushButton()
        self.trash_button.setIcon(build_simple_icon("trash", "#c4322b", 36))
        self.trash_button.setIconSize(QtCore.QSize(23, 23))
        self.trash_button.setObjectName("InlineTrashButton")
        self.trash_button.setToolTip(trash_tooltip)
        self.trash_button.setFixedSize(30, 30)
        self.trash_button.hide()

        layout.addLayout(text_layout, stretch=1)
        layout.addWidget(self.trash_button)

        self.trash_button.clicked.connect(lambda: self.trashRequested.emit(self.note_id))

    def set_selected(self, is_selected: bool) -> None:
        self.setProperty("active", is_selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def enterEvent(self, event: QtCore.QEvent) -> None:
        self.trash_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self.trash_button.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self.selectedRequested.emit(self.note_id)
        super().mousePressEvent(event)


class TrashNoteWidget(QtWidgets.QFrame):
    restoreRequested = QtCore.Signal(str)
    deleteRequested = QtCore.Signal(str)

    def __init__(
        self,
        note: Note,
        updated_label: str,
        parent: QtWidgets.QWidget | None = None,
        restore_text: str = "Przywróć",
        delete_text: str = "Usuń",
    ) -> None:
        super().__init__(parent)
        self.note_id = note.id
        self.setObjectName("TrashNoteWidget")
        self.setMouseTracking(True)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 10, 10)
        layout.setSpacing(10)

        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)
        self.title_label = QtWidgets.QLabel(note.display_title)
        self.title_label.setObjectName("TrashNoteTitle")
        self.date_label = QtWidgets.QLabel(updated_label)
        self.date_label.setObjectName("TrashNoteMeta")
        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.date_label)

        self.restore_button = QtWidgets.QPushButton(restore_text)
        self.restore_button.setObjectName("TrashRestoreButton")
        self.delete_button = QtWidgets.QPushButton(delete_text)
        self.delete_button.setObjectName("TrashDeleteButton")
        self.restore_button.hide()
        self.delete_button.hide()

        layout.addLayout(text_layout, stretch=1)
        layout.addWidget(self.restore_button)
        layout.addWidget(self.delete_button)

        self.restore_button.clicked.connect(lambda: self.restoreRequested.emit(self.note_id))
        self.delete_button.clicked.connect(lambda: self.deleteRequested.emit(self.note_id))

    def enterEvent(self, event: QtCore.QEvent) -> None:
        self.restore_button.show()
        self.delete_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self.restore_button.hide()
        self.delete_button.hide()
        super().leaveEvent(event)


class TrashDialog(QtWidgets.QDialog):
    def __init__(self, repository: FileNoteRepository, translator, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.repository = repository
        self._tr = translator
        self.changed = False

        self.setWindowTitle(self._tr("trash_dialog_title"))
        self.resize(560, 480)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 18)
        layout.setSpacing(14)

        title = QtWidgets.QLabel(self._tr("trash_dialog_title"))
        title.setObjectName("DialogTitle")
        subtitle = QtWidgets.QLabel(self._tr("trash_dialog_description"))
        subtitle.setObjectName("DialogSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.empty_label = QtWidgets.QLabel(self._tr("trash_empty"))
        self.empty_label.setObjectName("TrashEmpty")
        self.empty_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.setObjectName("TrashList")
        self.list_widget.setSpacing(6)
        layout.addWidget(self.list_widget, stretch=1)
        layout.addWidget(self.empty_label, stretch=1)

        close_button = QtWidgets.QPushButton(self._tr("dialog_close"))
        close_button.setObjectName("DialogCloseButton")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        self._refresh()

    def _refresh(self) -> None:
        notes = self.repository.list_trashed_notes()
        self.list_widget.clear()
        self.list_widget.setVisible(bool(notes))
        self.empty_label.setVisible(not notes)

        for note in notes:
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.ItemDataRole.UserRole, note.id)
            item.setSizeHint(QtCore.QSize(500, 66))
            self.list_widget.addItem(item)

            widget = TrashNoteWidget(
                note,
                self._format_datetime(note.updated_at),
                self.list_widget,
                restore_text=self._tr("trash_restore_action"),
                delete_text=self._tr("trash_delete_action"),
            )
            widget.restoreRequested.connect(self._restore_note)
            widget.deleteRequested.connect(self._delete_note_permanently)
            self.list_widget.setItemWidget(item, widget)

    def _restore_note(self, note_id: str) -> None:
        self.repository.restore_from_trash(note_id)
        self.changed = True
        self._refresh()

    def _delete_note_permanently(self, note_id: str) -> None:
        note = self.repository.get_trashed_note(note_id)
        message_box = QtWidgets.QMessageBox(self)
        message_box.setWindowTitle(self._tr("trash_delete_title"))
        message_box.setText(self._tr("trash_delete_text", title=note.display_title))
        delete_button = message_box.addButton(
            self._tr("trash_delete_confirm"),
            QtWidgets.QMessageBox.ButtonRole.DestructiveRole,
        )
        message_box.addButton(self._tr("dialog_cancel"), QtWidgets.QMessageBox.ButtonRole.RejectRole)
        message_box.exec()

        if message_box.clickedButton() != delete_button:
            return

        self.repository.delete_from_trash(note_id)
        self.changed = True
        self._refresh()

    def _format_datetime(self, value) -> str:
        return value.astimezone().strftime("%d.%m.%Y, %H:%M")
