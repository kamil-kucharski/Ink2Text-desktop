from __future__ import annotations

from html import escape
import math
from pathlib import Path
import tempfile
from typing import Iterable
from datetime import datetime

from PySide6 import QtCore, QtGui, QtWidgets

from app.config import AppConfig, load_app_config, save_app_config
from app.models import Note
from app.services import (
    AIProvider,
    AIProviderError,
    GeminiAIProvider,
    ImagePreparationService,
    PDFExportPayload,
    TranscriptionResult,
    convert_note_content_to_editor_html,
    export_note_to_pdf,
)
from app.storage import FileNoteRepository
from app.ui.image_import import filter_supported_image_paths
from app.ui.i18n import translate
from app.ui.menu_select import MenuSelectButton
from app.ui.settings_dialog import AISettingsDialog
from app.ui.theme import apply_card_shadow


IMAGE_REORDER_MIME = "application/x-ink2text-image-path"


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


def build_simple_icon(kind: str, color: str = "#1f2937", size: int = 24) -> QtGui.QIcon:
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    painter.scale(size / 24, size / 24)
    pen = QtGui.QPen(QtGui.QColor(color))
    pen.setWidthF(2.0)
    pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

    if kind == "trash":
        painter.drawLine(7, 8, 17, 8)
        painter.drawLine(10, 6, 14, 6)
        painter.drawRoundedRect(QtCore.QRectF(8.5, 9.5, 7, 8.5), 1.5, 1.5)
        painter.drawLine(11, 11.5, 11, 16)
        painter.drawLine(13, 11.5, 13, 16)
    elif kind == "sparkle":
        painter.drawLine(12, 4, 12, 10)
        painter.drawLine(12, 14, 12, 20)
        painter.drawLine(4, 12, 10, 12)
        painter.drawLine(14, 12, 20, 12)
        painter.drawLine(7, 7, 9, 9)
        painter.drawLine(15, 15, 17, 17)
        painter.drawLine(17, 7, 15, 9)
        painter.drawLine(9, 15, 7, 17)
    elif kind == "clock":
        painter.drawEllipse(QtCore.QPointF(12, 12), 6, 6)
        painter.drawLine(12, 8.5, 12, 12)
        painter.drawLine(12, 12, 15, 13.5)
    elif kind == "calendar":
        painter.drawRoundedRect(QtCore.QRectF(6, 7, 12, 11), 1.5, 1.5)
        painter.drawLine(6, 10, 18, 10)
        painter.drawLine(9, 5, 9, 8)
        painter.drawLine(15, 5, 15, 8)
    elif kind == "image":
        painter.drawRoundedRect(QtCore.QRectF(6, 7, 12, 10), 1.5, 1.5)
        painter.drawEllipse(QtCore.QPointF(10, 10), 1.1, 1.1)
        painter.drawLine(8, 15, 11, 12)
        painter.drawLine(11, 12, 14, 15)
        painter.drawLine(14, 15, 16, 13)
    elif kind == "text":
        painter.drawLine(7, 7, 17, 7)
        painter.drawLine(7, 11, 17, 11)
        painter.drawLine(7, 15, 13, 15)
    elif kind == "globe":
        painter.drawEllipse(QtCore.QPointF(12, 12), 6, 6)
        painter.drawLine(6, 12, 18, 12)
        painter.drawArc(QtCore.QRectF(8, 6, 8, 12), 90 * 16, 180 * 16)
        painter.drawArc(QtCore.QRectF(8, 6, 8, 12), -90 * 16, 180 * 16)
    elif kind == "bulb":
        painter.drawEllipse(QtCore.QPointF(12, 10), 4, 4)
        painter.drawLine(10, 14, 14, 14)
        painter.drawLine(10.5, 16, 13.5, 16)
        painter.drawLine(12, 3.5, 12, 5)
        painter.drawLine(6.8, 5.2, 7.8, 6.2)
        painter.drawLine(17.2, 5.2, 16.2, 6.2)
        painter.drawLine(5, 10, 6.5, 10)
        painter.drawLine(17.5, 10, 19, 10)
    elif kind == "settings":
        painter.drawEllipse(QtCore.QPointF(12, 12), 3.2, 3.2)
        for angle in range(0, 360, 45):
            transform = QtGui.QTransform()
            transform.translate(12, 12)
            transform.rotate(angle)
            line = transform.map(QtCore.QLineF(0, -7, 0, -5.2))
            painter.drawLine(line)
    elif kind == "save":
        painter.drawRoundedRect(QtCore.QRectF(6, 5, 12, 14), 1.5, 1.5)
        painter.drawRoundedRect(QtCore.QRectF(9, 6, 6, 4), 0.8, 0.8)
        painter.drawRoundedRect(QtCore.QRectF(9, 14, 6, 5), 0.8, 0.8)
        painter.drawLine(15, 5, 18, 8)
    elif kind == "pdf":
        painter.drawRoundedRect(QtCore.QRectF(7, 4, 10, 16), 1.5, 1.5)
        painter.drawLine(13, 4, 17, 8)
        painter.drawLine(13, 4, 13, 8)
        painter.drawLine(13, 8, 17, 8)
        painter.drawLine(9, 14, 15, 14)
        painter.drawLine(9, 17, 14, 17)
    elif kind == "export":
        painter.drawRoundedRect(QtCore.QRectF(6, 8, 12, 11), 1.5, 1.5)
        painter.drawLine(12, 15, 12, 4)
        painter.drawLine(8.5, 7.5, 12, 4)
        painter.drawLine(15.5, 7.5, 12, 4)
        painter.drawLine(9, 15.5, 15, 15.5)
    elif kind == "edit":
        painter.save()
        painter.translate(12, 12)
        painter.rotate(45)
        painter.drawRoundedRect(QtCore.QRectF(-2.2, -8.0, 4.4, 12.0), 1.2, 1.2)
        painter.drawLine(-2.2, -4.8, 2.2, -4.8)
        pencil_tip = QtGui.QPolygonF(
            [
                QtCore.QPointF(-2.2, 4.0),
                QtCore.QPointF(2.2, 4.0),
                QtCore.QPointF(0.0, 7.6),
            ]
        )
        painter.drawPolygon(pencil_tip)
        painter.drawLine(-0.7, 6.2, 0.7, 6.2)
        painter.restore()
    elif kind == "expand":
        painter.drawLine(5, 9, 5, 5)
        painter.drawLine(5, 5, 9, 5)
        painter.drawLine(15, 5, 19, 5)
        painter.drawLine(19, 5, 19, 9)
        painter.drawLine(19, 15, 19, 19)
        painter.drawLine(19, 19, 15, 19)
        painter.drawLine(9, 19, 5, 19)
        painter.drawLine(5, 19, 5, 15)

    painter.end()
    return QtGui.QIcon(pixmap)


class NoteListItemWidget(QtWidgets.QFrame):
    selectedRequested = QtCore.Signal(str)
    trashRequested = QtCore.Signal(str)

    def __init__(self, note: Note, updated_label: str, parent: QtWidgets.QWidget | None = None) -> None:
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
        self.trash_button.setToolTip("Przenieś do kosza")
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

    def __init__(self, note: Note, updated_label: str, parent: QtWidgets.QWidget | None = None) -> None:
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

        self.restore_button = QtWidgets.QPushButton("Przywróć")
        self.restore_button.setObjectName("TrashRestoreButton")
        self.delete_button = QtWidgets.QPushButton("Usuń")
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

            widget = TrashNoteWidget(note, self._format_datetime(note.updated_at), self.list_widget)
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


class ImageListWidget(QtWidgets.QListWidget):
    imageReorderRequested = QtCore.Signal(str, int)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DropOnly)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(IMAGE_REORDER_MIME):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:
        if event.mimeData().hasFormat(IMAGE_REORDER_MIME):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        if not event.mimeData().hasFormat(IMAGE_REORDER_MIME):
            event.ignore()
            return

        relative_path = bytes(event.mimeData().data(IMAGE_REORDER_MIME)).decode("utf-8")
        insert_index = self._drop_insert_index(event.position().toPoint())
        source_row = self._row_for_relative_path(relative_path)
        if source_row is None:
            event.ignore()
            return

        if source_row < insert_index:
            insert_index -= 1
        if source_row == insert_index:
            event.acceptProposedAction()
            return

        self.imageReorderRequested.emit(relative_path, insert_index)
        event.acceptProposedAction()

    def _drop_insert_index(self, position: QtCore.QPoint) -> int:
        target_item = self.itemAt(position)
        if target_item is None:
            return self.count()

        target_row = self.row(target_item)
        target_rect = self.visualItemRect(target_item)
        if position.x() > target_rect.center().x():
            target_row += 1
        return target_row

    def _row_for_relative_path(self, relative_path: str) -> int | None:
        for row in range(self.count()):
            item = self.item(row)
            if item.data(QtCore.Qt.ItemDataRole.UserRole) == relative_path:
                return row
        return None


class ImageThumbnailWidget(QtWidgets.QFrame):
    selectedRequested = QtCore.Signal(str)
    previewRequested = QtCore.Signal(str)
    removeRequested = QtCore.Signal(str)
    reorderRequested = QtCore.Signal(str, str, bool)

    def __init__(self, relative_path: str, image_path: Path, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.relative_path = relative_path
        self.image_path = image_path
        self._press_pos: QtCore.QPoint | None = None
        self._drag_started = False
        self.setObjectName("ImageThumbnailWidget")
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(152, 116)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)

        self.image_label = QtWidgets.QLabel()
        self.image_label.setObjectName("ThumbnailImage")
        self.image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(142, 106)
        self.image_label.setPixmap(self._thumbnail_pixmap())
        self.image_label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.trash_button = QtWidgets.QPushButton()
        self.trash_button.setObjectName("ThumbnailTrashButton")
        self.trash_button.setIcon(build_simple_icon("trash", "#c4322b", 36))
        self.trash_button.setIconSize(QtCore.QSize(22, 22))
        self.trash_button.setFixedSize(34, 34)
        self.trash_button.hide()

        layout.addWidget(self.image_label, 0, 0)
        layout.addWidget(
            self.trash_button,
            0,
            0,
            alignment=QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignRight,
        )

        self.trash_button.clicked.connect(lambda: self.removeRequested.emit(self.relative_path))

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
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
            self._drag_started = False
            self.selectedRequested.emit(self.relative_path)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if (
            self._press_pos is not None
            and not self._drag_started
            and event.buttons() & QtCore.Qt.MouseButton.LeftButton
            and (event.position().toPoint() - self._press_pos).manhattanLength()
            >= QtWidgets.QApplication.startDragDistance()
        ):
            self._drag_started = True
            drag = QtGui.QDrag(self)
            mime_data = QtCore.QMimeData()
            mime_data.setData(IMAGE_REORDER_MIME, self.relative_path.encode("utf-8"))
            drag.setMimeData(mime_data)
            drag.setPixmap(self.grab())
            drag.setHotSpot(self._press_pos)
            drag.exec(QtCore.Qt.DropAction.MoveAction)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            should_preview = (
                self._press_pos is not None
                and not self._drag_started
                and self.rect().contains(event.position().toPoint())
            )
            self._press_pos = None
            self._drag_started = False
            if should_preview:
                self.previewRequested.emit(self.relative_path)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        if self._drop_source_path(event.mimeData()):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:
        if self._drop_source_path(event.mimeData()):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        source_path = self._drop_source_path(event.mimeData())
        if not source_path:
            event.ignore()
            return

        insert_after_target = event.position().x() > self.width() / 2
        self.reorderRequested.emit(source_path, self.relative_path, insert_after_target)
        event.acceptProposedAction()

    def _drop_source_path(self, mime_data: QtCore.QMimeData) -> str | None:
        if not mime_data.hasFormat(IMAGE_REORDER_MIME):
            return None

        source_path = bytes(mime_data.data(IMAGE_REORDER_MIME)).decode("utf-8")
        if source_path == self.relative_path:
            return None
        return source_path

    def _thumbnail_pixmap(self) -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap(str(self.image_path))
        if pixmap.isNull():
            fallback = QtGui.QPixmap(142, 106)
            fallback.fill(QtGui.QColor("#f1f5fb"))
            return fallback

        return pixmap.scaled(
            142,
            106,
            QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )


class ImagePreviewDialog(QtWidgets.QDialog):
    def __init__(
        self,
        image_path: Path,
        title: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.image_path = image_path
        self.original_pixmap = QtGui.QPixmap(str(image_path))
        self.setWindowTitle(title)
        self.resize(900, 680)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 14)
        layout.setSpacing(12)

        self.image_label = QtWidgets.QLabel()
        self.image_label.setObjectName("PreviewImage")
        self.image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(520, 420)
        layout.addWidget(self.image_label, stretch=1)

        close_button = QtWidgets.QPushButton("Zamknij")
        close_button.setObjectName("DialogCloseButton")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        self._update_preview()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_preview()

    def _update_preview(self) -> None:
        if self.original_pixmap.isNull():
            self.image_label.setText("Nie udało się wczytać podglądu")
            return

        self.image_label.setPixmap(
            self.original_pixmap.scaled(
                self.image_label.size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        )


class PDFPreviewDialog(QtWidgets.QDialog):
    def __init__(
        self,
        pdf_path: Path,
        title: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        try:
            from PySide6 import QtPdf, QtPdfWidgets
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "Brakuje modułów Qt potrzebnych do podglądu PDF. "
                "Upewnij się, że PySide6 jest poprawnie zainstalowane."
            ) from error

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
        self.fit_width_button = QtWidgets.QPushButton("Dopasuj")
        self.fit_width_button.setObjectName("DialogCloseButton")
        toolbar.addWidget(self.zoom_out_button)
        toolbar.addWidget(self.zoom_label)
        toolbar.addWidget(self.zoom_in_button)
        toolbar.addWidget(self.fit_width_button)
        layout.addLayout(toolbar)

        self.pdf_document = QtPdf.QPdfDocument(self)
        load_error = self.pdf_document.load(str(pdf_path))
        if load_error != QtPdf.QPdfDocument.Error.None_:
            raise RuntimeError("Nie udało się wczytać wygenerowanego podglądu PDF.")

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
        self.zoom_label.setText("Auto")

    def _update_zoom_label(self) -> None:
        self.zoom_label.setText(f"{round(self._zoom_factor * 100)}%")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.pdf_document.close()
        try:
            self.pdf_path.unlink(missing_ok=True)
        except OSError:
            pass
        super().closeEvent(event)


class LoadingSpinner(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._angle = 0
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self.setFixedSize(86, 86)

    def start(self) -> None:
        self._timer.start()
        self.show()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _tick(self) -> None:
        self._angle = (self._angle + 5) % 360
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(10, 10, -10, -10)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        segment_count = 72
        segment_span = 360 / segment_count
        dark_color = QtGui.QColor(30, 58, 138)
        light_color = QtGui.QColor(30, 58, 138)

        for segment in range(segment_count):
            progress = segment / (segment_count - 1)
            end_fade = math.sin(progress * math.pi)
            blue_strength = min(1.0, max(0.0, (progress - 0.38) / 0.42))
            alpha = int((24 + 196 * blue_strength) * end_fade)
            color = QtGui.QColor(dark_color if blue_strength > 0.5 else light_color)
            color.setAlpha(alpha)
            pen = QtGui.QPen(color, 9)
            pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            start_angle = int((self._angle - segment * segment_span) * 16)
            span_angle = int(-segment_span * 0.82 * 16)
            painter.drawArc(rect, start_angle, span_angle)

        pen = QtGui.QPen(QtGui.QColor(30, 58, 138, 12), 9)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(rect)


class LoadingOverlay(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("LoadingOverlay")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hide()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.card = QtWidgets.QFrame()
        self.card.setObjectName("LoadingCard")
        card_layout = QtWidgets.QVBoxLayout(self.card)
        card_layout.setContentsMargins(34, 30, 34, 28)
        card_layout.setSpacing(16)
        card_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.spinner = LoadingSpinner(self.card)
        self.label = QtWidgets.QLabel()
        self.label.setObjectName("LoadingLabel")
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(self.spinner, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.label)
        layout.addWidget(self.card)

    def set_text(self, text: str) -> None:
        self.label.setText(text)

    def start(self) -> None:
        self.setGeometry(self.parentWidget().rect() if self.parentWidget() else self.geometry())
        self.raise_()
        self.show()
        self.spinner.start()

    def stop(self) -> None:
        self.spinner.stop()
        self.hide()


class ResponsiveEditorToolbar(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[QtWidgets.QWidget] = []
        self._actions: list[QtGui.QAction] = []
        self._icon_size = QtCore.QSize(22, 22)
        self._row_count = 1
        self._layout = QtWidgets.QGridLayout(self)
        self._layout.setContentsMargins(10, 8, 10, 8)
        self._layout.setHorizontalSpacing(6)
        self._layout.setVerticalSpacing(6)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Maximum)

    def setMovable(self, _is_movable: bool) -> None:
        return

    def setFloatable(self, _is_floatable: bool) -> None:
        return

    def setIconSize(self, icon_size: QtCore.QSize) -> None:
        self._icon_size = icon_size
        for item in self._items:
            if isinstance(item, QtWidgets.QToolButton):
                item.setIconSize(icon_size)

    def addAction(self, icon: QtGui.QIcon, text: str = "") -> QtGui.QAction:  # type: ignore[override]
        action = QtGui.QAction(icon, text, self)
        button = QtWidgets.QToolButton(self)
        button.setDefaultAction(action)
        button.setAutoRaise(True)
        button.setIconSize(self._icon_size)
        button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._actions.append(action)
        QtWidgets.QWidget.addAction(self, action)
        self._add_item(button)
        return action

    def addWidget(self, widget: QtWidgets.QWidget) -> QtWidgets.QWidget:  # type: ignore[override]
        self._add_item(widget)
        return widget

    def addSeparator(self) -> None:
        separator = QtWidgets.QFrame(self)
        separator.setObjectName("ToolbarSeparator")
        separator.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        separator.setFixedWidth(1)
        self._add_item(separator)

    def actions(self) -> list[QtGui.QAction]:  # type: ignore[override]
        return self._actions

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._reflow()

    def _add_item(self, widget: QtWidgets.QWidget) -> None:
        self._items.append(widget)
        QtCore.QTimer.singleShot(0, self._reflow)

    def _reflow(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget() is not None:
                self._layout.removeWidget(item.widget())

        available_width = max(220, self.width() - 20)
        row = 0
        column = 0
        row_width = 0
        spacing = self._layout.horizontalSpacing()

        for widget in self._items:
            item_width = self._item_width(widget)
            next_width = item_width if row_width == 0 else row_width + spacing + item_width
            if row == 0 and row_width > 0 and next_width > available_width:
                row = 1
                column = 0
                row_width = 0

            self._layout.addWidget(widget, row, column)
            row_width = item_width if row_width == 0 else row_width + spacing + item_width
            column += 1

        self._row_count = row + 1
        margins = self._layout.contentsMargins()
        row_height = 36
        height = margins.top() + margins.bottom() + self._row_count * row_height
        if self._row_count > 1:
            height += self._layout.verticalSpacing()
        self.setMinimumHeight(height)
        self.setMaximumHeight(height)
        self.updateGeometry()

    def _item_width(self, widget: QtWidgets.QWidget) -> int:
        if widget.objectName() == "ToolbarSeparator":
            return 11
        return max(widget.minimumSizeHint().width(), widget.sizeHint().width(), widget.minimumWidth())


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

    def _build_legacy_ui(self) -> None:
        central_widget = QtWidgets.QWidget()
        central_widget.setObjectName("AppRoot")
        root_layout = QtWidgets.QVBoxLayout(central_widget)
        root_layout.setContentsMargins(24, 22, 24, 20)
        root_layout.setSpacing(18)

        self.header_card = QtWidgets.QFrame()
        self.header_card.setObjectName("HeaderBar")
        header_layout = QtWidgets.QVBoxLayout(self.header_card)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(14)

        self.header_eyebrow = QtWidgets.QLabel()
        self.header_eyebrow.setObjectName("HeaderEyebrow")
        self.hero_title = QtWidgets.QLabel()
        self.hero_title.setObjectName("HeroTitle")
        self.hero_subtitle = QtWidgets.QLabel()
        self.hero_subtitle.setObjectName("HeroSubtitle")
        self.hero_subtitle.setWordWrap(True)
        self.note_count_badge = QtWidgets.QLabel()
        self.note_count_badge.setObjectName("CountBadge")
        self.note_count_badge.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        hero_top_row = QtWidgets.QHBoxLayout()
        hero_top_row.setSpacing(14)
        hero_text_layout = QtWidgets.QVBoxLayout()
        hero_text_layout.setSpacing(4)
        hero_text_layout.addWidget(self.header_eyebrow)
        hero_text_layout.addWidget(self.hero_title)
        hero_text_layout.addWidget(self.hero_subtitle)
        utility_layout = QtWidgets.QHBoxLayout()
        utility_layout.setSpacing(10)
        utility_layout.addStretch()
        utility_layout.addWidget(self.note_count_badge, alignment=QtCore.Qt.AlignmentFlag.AlignTop)
        hero_top_row.addLayout(hero_text_layout, stretch=1)
        hero_top_row.addLayout(utility_layout)

        action_layout = QtWidgets.QHBoxLayout()
        action_layout.setSpacing(12)
        left_action_group = QtWidgets.QHBoxLayout()
        left_action_group.setSpacing(8)
        right_action_group = QtWidgets.QHBoxLayout()
        right_action_group.setSpacing(8)
        self.new_button = QtWidgets.QPushButton("Nowa notatka")
        self.save_button = QtWidgets.QPushButton("Zapisz")
        self.delete_note_button = QtWidgets.QPushButton("Usuń notatkę")
        self.export_pdf_button = QtWidgets.QPushButton("Eksportuj PDF")
        self.refresh_button = QtWidgets.QPushButton("Odśwież")
        self.import_images_button = QtWidgets.QPushButton("Importuj zdjęcia")
        self.transcribe_ai_button = QtWidgets.QPushButton("Przetwórz przez AI")
        self.ai_settings_button = QtWidgets.QPushButton("Ustawienia AI")
        self.language_button = MenuSelectButton()
        self.language_button.setObjectName("LanguageButton")
        self.language_button.addItem("Polski", "pl")
        self.language_button.addItem("English", "en")
        self.language_button.setCurrentData(self.app_language)
        self.language_button.setMinimumWidth(126)
        left_action_group.addWidget(self.new_button)
        left_action_group.addWidget(self.save_button)
        left_action_group.addWidget(self.export_pdf_button)
        left_action_group.addWidget(self.delete_note_button)
        right_action_group.addWidget(self.refresh_button)
        right_action_group.addWidget(self.ai_settings_button)
        right_action_group.addWidget(self.language_button)
        action_layout.addLayout(left_action_group)
        action_layout.addStretch()
        action_layout.addLayout(right_action_group)

        header_layout.addLayout(hero_top_row)
        header_layout.addLayout(action_layout)

        self.workspace_shell = QtWidgets.QFrame()
        self.workspace_shell.setObjectName("WorkspaceShell")
        workspace_layout = QtWidgets.QVBoxLayout(self.workspace_shell)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        splitter = QtWidgets.QSplitter()
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(14)

        left_panel = QtWidgets.QFrame()
        left_panel.setObjectName("SidebarPane")
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 20, 16, 20)
        left_layout.setSpacing(12)
        self.saved_notes_label = QtWidgets.QLabel()
        self.saved_notes_label.setObjectName("SectionLabel")
        left_layout.addWidget(self.saved_notes_label)
        self.note_list = QtWidgets.QListWidget()
        self.note_list.setObjectName("NoteList")
        left_layout.addWidget(self.note_list)

        right_panel = QtWidgets.QFrame()
        right_panel.setObjectName("ContentPane")
        form_layout = QtWidgets.QVBoxLayout(right_panel)
        form_layout.setContentsMargins(18, 20, 20, 20)
        form_layout.setSpacing(14)

        self.meta_section = QtWidgets.QFrame()
        self.meta_section.setObjectName("MetaSection")
        meta_layout = QtWidgets.QVBoxLayout(self.meta_section)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(14)
        title_row = QtWidgets.QHBoxLayout()
        title_row.setSpacing(12)
        title_text_layout = QtWidgets.QVBoxLayout()
        title_text_layout.setSpacing(8)
        self.title_label = QtWidgets.QLabel()
        self.title_label.setObjectName("SectionLabel")
        title_text_layout.addWidget(self.title_label)
        self.title_input = QtWidgets.QLineEdit()
        self.title_input.setObjectName("TitleInput")
        title_text_layout.addWidget(self.title_input)
        title_row.addLayout(title_text_layout, stretch=1)

        mode_layout = QtWidgets.QVBoxLayout()
        mode_layout.setSpacing(8)
        self.transcription_mode_label = QtWidgets.QLabel()
        self.transcription_mode_label.setObjectName("ModeInlineLabel")
        mode_layout.addWidget(self.transcription_mode_label)
        self.transcription_mode_input = MenuSelectButton()
        self.transcription_mode_input.setObjectName("ModeButton")
        self.transcription_mode_input.setMinimumWidth(240)
        mode_layout.addWidget(self.transcription_mode_input)
        title_row.addLayout(mode_layout)
        meta_layout.addLayout(title_row)

        quick_actions_row = QtWidgets.QHBoxLayout()
        quick_actions_row.setSpacing(8)
        quick_actions_row.addWidget(self.import_images_button)
        quick_actions_row.addWidget(self.transcribe_ai_button)
        quick_actions_row.addStretch()
        meta_layout.addLayout(quick_actions_row)

        self.images_section = QtWidgets.QFrame()
        self.images_section.setObjectName("ImagesSection")
        images_layout = QtWidgets.QVBoxLayout(self.images_section)
        images_layout.setContentsMargins(0, 0, 0, 0)
        images_layout.setSpacing(10)
        attachments_layout = QtWidgets.QHBoxLayout()
        attachments_layout.setSpacing(8)
        self.attachments_header = QtWidgets.QLabel()
        self.attachments_header.setObjectName("SectionLabel")
        self.move_image_earlier_button = QtWidgets.QPushButton("Wcześniej")
        self.move_image_later_button = QtWidgets.QPushButton("Później")
        self.remove_image_button = QtWidgets.QPushButton("Usuń zaznaczone zdjęcie")
        attachments_layout.addWidget(self.attachments_header)
        attachments_layout.addStretch()
        attachments_layout.addWidget(self.move_image_earlier_button)
        attachments_layout.addWidget(self.move_image_later_button)
        attachments_layout.addWidget(self.remove_image_button)
        images_layout.addLayout(attachments_layout)
        image_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        image_splitter.setChildrenCollapsible(False)
        image_splitter.setHandleWidth(10)
        self.image_list = ImageListWidget()
        self.image_list.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        self.image_list.setFlow(QtWidgets.QListView.Flow.LeftToRight)
        self.image_list.setWrapping(True)
        self.image_list.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.image_list.setMovement(QtWidgets.QListView.Movement.Static)
        self.image_list.setIconSize(QtCore.QSize(96, 96))
        self.image_list.setGridSize(QtCore.QSize(132, 132))
        self.image_list.setSpacing(10)
        self.image_list.setObjectName("ImageList")
        self.image_preview = QtWidgets.QLabel()
        self.image_preview.setObjectName("ImagePreview")
        self.image_preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMinimumHeight(220)
        self.image_preview.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        image_splitter.addWidget(self.image_list)
        image_splitter.addWidget(self.image_preview)
        image_splitter.setStretchFactor(0, 1)
        image_splitter.setStretchFactor(1, 2)
        image_splitter.setSizes([340, 520])
        images_layout.addWidget(image_splitter)
        self.drag_hint = QtWidgets.QLabel()
        self.drag_hint.setObjectName("StatusPill")
        images_layout.addWidget(self.drag_hint, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)

        self.editor_section = QtWidgets.QFrame()
        self.editor_section.setObjectName("EditorSection")
        editor_layout = QtWidgets.QVBoxLayout(self.editor_section)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(10)
        self._build_editor_toolbar()
        editor_layout.addWidget(self.editor_toolbar)
        self.content_input = QtWidgets.QTextEdit()
        self.content_input.setAcceptRichText(True)
        self.content_input.setObjectName("ContentEditor")
        self.content_input.setMinimumHeight(360)
        editor_layout.addWidget(self.content_input, stretch=1)

        self.right_splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        self.right_splitter.setChildrenCollapsible(False)
        self.right_splitter.setHandleWidth(12)
        top_right_widget = QtWidgets.QWidget()
        top_right_layout = QtWidgets.QVBoxLayout(top_right_widget)
        top_right_layout.setContentsMargins(0, 0, 0, 0)
        top_right_layout.setSpacing(18)
        top_right_layout.addWidget(self.meta_section)
        top_right_layout.addWidget(self.images_section, stretch=1)
        self.right_splitter.addWidget(top_right_widget)
        self.right_splitter.addWidget(self.editor_section)
        self.right_splitter.setStretchFactor(0, 1)
        self.right_splitter.setStretchFactor(1, 2)
        self.right_splitter.setSizes([320, 430])
        form_layout.addWidget(self.right_splitter, stretch=1)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setSizes([300, 980])

        workspace_layout.addWidget(splitter)

        root_layout.addWidget(self.header_card)
        root_layout.addWidget(self.workspace_shell, stretch=1)

        self.setCentralWidget(central_widget)
        self.statusBar().showMessage(self._tr("status_ready"))
        self._apply_visual_treatment()

        self.new_button.clicked.connect(self._create_new_note)
        self.export_pdf_button.clicked.connect(self._export_current_note_to_pdf)
        self.save_button.clicked.connect(self._save_current_note)
        self.delete_note_button.clicked.connect(self._delete_current_note)
        self.refresh_button.clicked.connect(self.refresh_notes)
        self.import_images_button.clicked.connect(self._import_images)
        self.transcribe_ai_button.clicked.connect(self._transcribe_current_note_with_ai)
        self.ai_settings_button.clicked.connect(self._open_ai_settings)
        self.move_image_earlier_button.clicked.connect(lambda: self._move_selected_image(-1))
        self.move_image_later_button.clicked.connect(lambda: self._move_selected_image(1))
        self.remove_image_button.clicked.connect(self._remove_selected_image)
        self.note_list.itemSelectionChanged.connect(self._load_selected_note)
        self.note_list.itemSelectionChanged.connect(self._sync_note_list_widget_selection)
        self.image_list.itemSelectionChanged.connect(self._update_image_preview)
        self.language_button.currentDataChanged.connect(self._change_language)
        self.content_input.currentCharFormatChanged.connect(self._sync_format_controls)
        self.content_input.cursorPositionChanged.connect(self._sync_format_controls)

    def _build_ui(self) -> None:
        self.resize(1280, 780)

        central_widget = QtWidgets.QWidget()
        central_widget.setObjectName("AppRoot")
        root_layout = QtWidgets.QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        app_layout = QtWidgets.QHBoxLayout()
        app_layout.setContentsMargins(0, 0, 0, 0)
        app_layout.setSpacing(0)

        self.sidebar = QtWidgets.QFrame()
        self.sidebar.setObjectName("SidebarPane")
        self.sidebar.setFixedWidth(268)
        sidebar_layout = QtWidgets.QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(20, 24, 20, 14)
        sidebar_layout.setSpacing(14)

        logo_row = QtWidgets.QHBoxLayout()
        logo_row.setSpacing(12)
        self.logo_mark = QtWidgets.QLabel()
        self.logo_mark.setObjectName("LogoMark")
        self.logo_mark.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        logo_path = Path(__file__).resolve().parents[2] / "assets" / "logoink2text.png"
        logo_pixmap = QtGui.QPixmap(str(logo_path))
        if not logo_pixmap.isNull():
            self.logo_mark.setPixmap(
                logo_pixmap.scaled(
                    38,
                    38,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
            )
        self.logo_label = QtWidgets.QLabel("Ink2Text")
        self.logo_label.setObjectName("LogoLabel")
        logo_row.addWidget(self.logo_mark)
        logo_row.addWidget(self.logo_label)
        logo_row.addStretch()
        sidebar_layout.addLayout(logo_row)

        self.new_button = QtWidgets.QPushButton("+  Nowa notatka")
        self.new_button.setObjectName("SidebarPrimaryButton")
        sidebar_layout.addWidget(self.new_button)

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setObjectName("SearchInput")
        self.search_input.setClearButtonEnabled(True)
        sidebar_layout.addWidget(self.search_input)

        notes_header = QtWidgets.QHBoxLayout()
        notes_header.setSpacing(8)
        self.saved_notes_label = QtWidgets.QLabel()
        self.saved_notes_label.setObjectName("SidebarSectionLabel")
        self.notes_count_label = QtWidgets.QLabel()
        self.notes_count_label.setObjectName("SidebarCountLabel")
        notes_header.addWidget(self.saved_notes_label)
        notes_header.addStretch()
        notes_header.addWidget(self.notes_count_label)
        sidebar_layout.addLayout(notes_header)

        self.note_list = QtWidgets.QListWidget()
        self.note_list.setObjectName("NoteList")
        self.note_list.setSpacing(4)
        sidebar_layout.addWidget(self.note_list, stretch=1)

        self.trash_button = QtWidgets.QPushButton("Kosz")
        self.trash_button.setObjectName("SidebarLinkButton")
        self.trash_button.setIcon(build_simple_icon("trash", "#7b879d", 36))
        self.trash_button.setIconSize(QtCore.QSize(22, 22))
        sidebar_layout.addWidget(self.trash_button)

        main_area = QtWidgets.QWidget()
        main_area.setObjectName("MainArea")
        main_layout = QtWidgets.QVBoxLayout(main_area)
        main_layout.setContentsMargins(18, 18, 18, 14)
        main_layout.setSpacing(4)

        self.top_bar = QtWidgets.QFrame()
        self.top_bar.setObjectName("TopBar")
        top_layout = QtWidgets.QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(0, 4, 0, 4)
        top_layout.setSpacing(14)

        title_shell = QtWidgets.QHBoxLayout()
        title_shell.setSpacing(14)
        self.save_button = QtWidgets.QPushButton()
        self.save_button.setObjectName("TitleIconButton")
        self.save_button.setIcon(build_simple_icon("save", "#172b65", 32))
        self.save_button.setIconSize(QtCore.QSize(21, 21))
        self.title_icon_tile = QtWidgets.QLabel()
        self.title_icon_tile.setObjectName("TitleIconTile")
        self.title_icon_tile.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.title_icon_tile.setPixmap(build_simple_icon("edit", "#172b65", 32).pixmap(21, 21))
        self.title_icon_tile.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.title_icon_tile.installEventFilter(self)
        title_shell.addWidget(self.save_button, alignment=QtCore.Qt.AlignmentFlag.AlignTop)
        title_shell.addWidget(self.title_icon_tile, alignment=QtCore.Qt.AlignmentFlag.AlignTop)
        title_shell.addSpacing(8)

        title_area = QtWidgets.QVBoxLayout()
        title_area.setSpacing(0)
        title_row = QtWidgets.QHBoxLayout()
        title_row.setSpacing(8)
        self.title_input = QtWidgets.QLineEdit()
        self.title_input.setObjectName("TitleInput")
        self.title_input.setClearButtonEnabled(False)
        self.note_meta_label = QtWidgets.QLabel()
        self.note_meta_label.setObjectName("MetaText")
        self.note_meta_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.note_meta_label.setContentsMargins(2, -2, 0, 0)
        title_row.addWidget(self.title_input)
        title_row.addStretch()
        title_area.addLayout(title_row)
        title_area.addWidget(self.note_meta_label)
        title_shell.addLayout(title_area, stretch=1)
        top_layout.addLayout(title_shell, stretch=1)
        self.settings_button = QtWidgets.QPushButton()
        self.settings_button.setObjectName("TitleIconButton")
        self.settings_button.setIcon(build_simple_icon("settings", "#172b65", 32))
        self.settings_button.setIconSize(QtCore.QSize(21, 21))
        top_layout.addWidget(self.settings_button, alignment=QtCore.Qt.AlignmentFlag.AlignTop)

        self.refresh_button = QtWidgets.QPushButton("Odśwież")

        content_row = QtWidgets.QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(0)

        center_column = QtWidgets.QVBoxLayout()
        center_column.setContentsMargins(0, 0, 0, 0)
        center_column.setSpacing(0)

        self.photos_card = QtWidgets.QFrame()
        self.photos_card.setObjectName("PhotosPanel")
        photos_layout = QtWidgets.QVBoxLayout(self.photos_card)
        photos_layout.setContentsMargins(18, 16, 18, 16)
        photos_layout.setSpacing(6)

        photos_header = QtWidgets.QHBoxLayout()
        photos_header.setSpacing(12)
        self.attachments_header = QtWidgets.QLabel()
        self.attachments_header.setObjectName("CardTitle")
        self.import_images_button = QtWidgets.QPushButton("+")
        self.import_images_button.setObjectName("AddImageButton")
        photos_header.addWidget(self.attachments_header)
        photos_header.addWidget(self.import_images_button)
        photos_header.addStretch()
        photos_layout.addLayout(photos_header)

        self.image_empty_label = QtWidgets.QLabel()
        self.image_empty_label.setObjectName("ThumbnailEmpty")
        self.image_empty_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.image_empty_label.setWordWrap(True)
        photos_layout.addWidget(self.image_empty_label)

        self.image_list = ImageListWidget()
        self.image_list.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        self.image_list.setFlow(QtWidgets.QListView.Flow.LeftToRight)
        self.image_list.setWrapping(True)
        self.image_list.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.image_list.setMovement(QtWidgets.QListView.Movement.Static)
        self.image_list.setGridSize(QtCore.QSize(164, 132))
        self.image_list.setSpacing(12)
        self.image_list.setObjectName("ImageList")
        self.image_list.setMinimumHeight(128)
        self.image_list.setMaximumHeight(134)
        photos_layout.addWidget(self.image_list)

        photos_hint_row = QtWidgets.QHBoxLayout()
        photos_hint_row.setContentsMargins(0, 0, 0, 0)
        photos_hint_row.setSpacing(12)
        self.drag_hint = QtWidgets.QLabel()
        self.drag_hint.setObjectName("HelperText")
        self.drag_hint.setContentsMargins(0, 0, 0, 0)
        self.image_order_hint = QtWidgets.QLabel()
        self.image_order_hint.setObjectName("HelperText")
        self.image_order_hint.setContentsMargins(0, 0, 0, 0)
        self.image_order_hint.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        photos_hint_row.addWidget(self.image_order_hint)
        photos_hint_row.addStretch()
        photos_hint_row.addWidget(self.drag_hint)
        photos_layout.addLayout(photos_hint_row)

        self.editor_section = QtWidgets.QFrame()
        self.editor_section.setObjectName("EditorPanel")
        editor_layout = QtWidgets.QVBoxLayout(self.editor_section)
        editor_layout.setContentsMargins(18, 16, 18, 16)
        editor_layout.setSpacing(10)

        editor_header = QtWidgets.QHBoxLayout()
        editor_header.setSpacing(12)
        self.editor_title_label = QtWidgets.QLabel()
        self.editor_title_label.setObjectName("CardTitle")
        self.export_pdf_button = QtWidgets.QPushButton()
        self.export_pdf_button.setObjectName("IconButton")
        self.export_pdf_button.setIcon(build_simple_icon("export", "#66728a", 32))
        self.export_pdf_button.setIconSize(QtCore.QSize(18, 18))
        self.pdf_preview_button = QtWidgets.QPushButton()
        self.pdf_preview_button.setObjectName("IconButton")
        self.pdf_preview_button.setIcon(build_simple_icon("expand", "#66728a", 32))
        self.pdf_preview_button.setIconSize(QtCore.QSize(18, 18))
        editor_header.addWidget(self.editor_title_label)
        editor_header.addStretch()
        editor_header.addWidget(self.export_pdf_button)
        editor_header.addWidget(self.pdf_preview_button)
        editor_layout.addLayout(editor_header)

        self._build_editor_toolbar()
        editor_layout.addWidget(self.editor_toolbar)

        self.content_input = QtWidgets.QTextEdit()
        self.content_input.setAcceptRichText(True)
        self.content_input.setObjectName("ContentEditor")
        self.content_input.setMinimumHeight(310)
        editor_layout.addWidget(self.content_input, stretch=1)

        center_column.addWidget(self.photos_card)
        center_column.addWidget(self.editor_section, stretch=1)
        content_row.addLayout(center_column, stretch=1)

        self.assistant_panel = QtWidgets.QFrame()
        self.assistant_panel.setObjectName("AssistantPanel")
        self.assistant_panel.setFixedWidth(304)
        assistant_layout = QtWidgets.QVBoxLayout(self.assistant_panel)
        assistant_layout.setContentsMargins(24, 26, 24, 24)
        assistant_layout.setSpacing(16)

        assistant_header = QtWidgets.QHBoxLayout()
        assistant_header.setSpacing(12)
        self.assistant_icon_label = QtWidgets.QLabel()
        self.assistant_icon_label.setObjectName("AssistantIcon")
        self.assistant_icon_label.setPixmap(build_simple_icon("sparkle", "#172b65", 32).pixmap(24, 24))
        self.assistant_title_label = QtWidgets.QLabel()
        self.assistant_title_label.setObjectName("AssistantTitle")
        assistant_header.addWidget(self.assistant_icon_label)
        assistant_header.addWidget(self.assistant_title_label)
        assistant_header.addStretch()
        assistant_layout.addLayout(assistant_header)

        self.assistant_mode_label = QtWidgets.QLabel()
        self.assistant_mode_label.setObjectName("AssistantSectionLabel")
        self.transcription_mode_input = MenuSelectButton()
        self.transcription_mode_input.setObjectName("AssistantModeButton")
        self.transcription_mode_input.setMinimumHeight(54)
        self.transcription_mode_input.setMinimumWidth(220)
        self.assistant_mode_description = QtWidgets.QLabel()
        self.assistant_mode_description.setObjectName("AssistantDescription")
        self.assistant_mode_description.setWordWrap(True)
        assistant_layout.addWidget(self.assistant_mode_label)
        assistant_layout.addWidget(self.transcription_mode_input)
        assistant_layout.addWidget(self.assistant_mode_description)

        assistant_separator = QtWidgets.QFrame()
        assistant_separator.setObjectName("AssistantSeparator")
        assistant_separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        assistant_layout.addWidget(assistant_separator)

        self.note_info_label = QtWidgets.QLabel()
        self.note_info_label.setObjectName("AssistantSectionLabel")
        assistant_layout.addWidget(self.note_info_label)

        self.info_created_label = QtWidgets.QLabel()
        self.info_updated_label = QtWidgets.QLabel()
        self.info_images_label = QtWidgets.QLabel()
        self.info_characters_label = QtWidgets.QLabel()
        self.info_created_value = QtWidgets.QLabel()
        self.info_updated_value = QtWidgets.QLabel()
        self.info_images_value = QtWidgets.QLabel()
        self.info_characters_value = QtWidgets.QLabel()
        for label in (
            self.info_created_label,
            self.info_updated_label,
            self.info_images_label,
            self.info_characters_label,
        ):
            label.setObjectName("InfoLabel")
        for label in (
            self.info_created_value,
            self.info_updated_value,
            self.info_images_value,
            self.info_characters_value,
        ):
            label.setObjectName("InfoValue")

        for label, value in (
            (self.info_created_label, self.info_created_value),
            (self.info_updated_label, self.info_updated_value),
            (self.info_images_label, self.info_images_value),
            (self.info_characters_label, self.info_characters_value),
        ):
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(10)
            icon_kind = (
                "clock"
                if label is self.info_created_label
                else "calendar"
                if label is self.info_updated_label
                else "image"
                if label is self.info_images_label
                else "text"
                if label is self.info_characters_label
                else "globe"
            )
            icon_label = QtWidgets.QLabel()
            icon_label.setObjectName("InfoIcon")
            icon_label.setPixmap(build_simple_icon(icon_kind, "#94a0b8", 28).pixmap(20, 20))
            row.addWidget(icon_label)
            label.setMinimumWidth(112)
            row.addWidget(label, stretch=1)
            row.addStretch()
            row.addWidget(value)
            assistant_layout.addLayout(row)

        self.transcribe_ai_button = QtWidgets.QPushButton("Przetwórz przez AI")
        self.transcribe_ai_button.setObjectName("AssistantPrimaryButton")
        assistant_layout.addWidget(self.transcribe_ai_button)

        assistant_layout.addStretch()

        self.tip_card = QtWidgets.QFrame()
        self.tip_card.setObjectName("TipCard")
        tip_layout = QtWidgets.QVBoxLayout(self.tip_card)
        tip_layout.setContentsMargins(16, 14, 16, 14)
        tip_layout.setSpacing(8)
        tip_header = QtWidgets.QHBoxLayout()
        tip_header.setSpacing(8)
        self.tip_icon_label = QtWidgets.QLabel()
        self.tip_icon_label.setObjectName("TipIcon")
        self.tip_icon_label.setPixmap(build_simple_icon("bulb", "#2563eb", 28).pixmap(18, 18))
        self.tip_title_label = QtWidgets.QLabel()
        self.tip_title_label.setObjectName("TipTitle")
        tip_header.addWidget(self.tip_icon_label)
        tip_header.addWidget(self.tip_title_label)
        tip_header.addStretch()
        self.tip_text_label = QtWidgets.QLabel()
        self.tip_text_label.setObjectName("TipText")
        self.tip_text_label.setWordWrap(True)
        tip_layout.addLayout(tip_header)
        tip_layout.addWidget(self.tip_text_label)
        assistant_layout.addWidget(self.tip_card)

        content_row.addWidget(self.assistant_panel)

        main_layout.addWidget(self.top_bar)
        main_layout.addLayout(content_row, stretch=1)

        app_layout.addWidget(self.sidebar)
        app_layout.addWidget(main_area, stretch=1)
        root_layout.addLayout(app_layout, stretch=1)

        self.setCentralWidget(central_widget)
        self.loading_overlay = LoadingOverlay(central_widget)
        self.loading_overlay.setGeometry(central_widget.rect())
        self.version_status_label = QtWidgets.QLabel("Ink2Text v1.1.5")
        self.version_status_label.setObjectName("StatusMeta")
        self.local_save_status_label = QtWidgets.QLabel()
        self.local_save_status_label.setObjectName("StatusMeta")
        self.statusBar().addPermanentWidget(self.version_status_label, stretch=1)
        self.statusBar().addPermanentWidget(self.local_save_status_label)
        self.statusBar().showMessage(self._tr("status_ready"))
        self._apply_visual_treatment()

        self.new_button.clicked.connect(self._create_new_note)
        self.export_pdf_button.clicked.connect(self._export_current_note_to_pdf)
        self.save_button.clicked.connect(self._save_current_note)
        self.refresh_button.clicked.connect(self.refresh_notes)
        self.import_images_button.clicked.connect(self._import_images)
        self.transcribe_ai_button.clicked.connect(self._transcribe_current_note_with_ai)
        self.pdf_preview_button.clicked.connect(self._open_current_note_pdf_preview)
        self.settings_button.clicked.connect(self._open_ai_settings)
        self.trash_button.clicked.connect(self._open_trash_dialog)
        self.note_list.itemSelectionChanged.connect(self._load_selected_note)
        self.image_list.itemSelectionChanged.connect(self._update_image_counter)
        self.image_list.imageReorderRequested.connect(self._reorder_image_to_index)
        self.transcription_mode_input.currentDataChanged.connect(lambda _mode: self._update_assistant_panel())
        self.search_input.textChanged.connect(lambda _text: self.refresh_notes())
        self.content_input.textChanged.connect(self._update_character_count)
        self.content_input.textChanged.connect(self._mark_note_as_unsaved)
        self.title_input.textChanged.connect(self._mark_note_as_unsaved)
        self.content_input.currentCharFormatChanged.connect(self._sync_format_controls)
        self.content_input.cursorPositionChanged.connect(self._sync_format_controls)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if watched is getattr(self, "title_icon_tile", None):
            if event.type() == QtCore.QEvent.Type.MouseButtonPress:
                self._select_note_title_for_editing()
                return True

        return super().eventFilter(watched, event)

    def _select_note_title_for_editing(self) -> None:
        self.title_input.setFocus(QtCore.Qt.FocusReason.MouseFocusReason)
        self.title_input.selectAll()

    def _build_editor_toolbar(self) -> None:
        toolbar = ResponsiveEditorToolbar()
        toolbar.setObjectName("EditorToolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QtCore.QSize(22, 22))
        self.editor_toolbar = toolbar

        self.undo_action = toolbar.addAction(self._build_toolbar_icon("undo"), "")
        self.undo_action.setToolTip("Cofnij")
        self.redo_action = toolbar.addAction(self._build_toolbar_icon("redo"), "")
        self.redo_action.setToolTip("Ponów")

        toolbar.addSeparator()
        self.bold_action = toolbar.addAction(self._build_toolbar_icon("bold"), "")
        self.bold_action.setCheckable(True)
        self.bold_action.setToolTip("Pogrubienie")

        self.italic_action = toolbar.addAction(self._build_toolbar_icon("italic"), "")
        self.italic_action.setCheckable(True)
        self.italic_action.setToolTip("Kursywa")

        self.underline_action = toolbar.addAction(self._build_toolbar_icon("underline"), "")
        self.underline_action.setCheckable(True)
        self.underline_action.setToolTip("Podkreślenie")
        self.strike_action = toolbar.addAction(self._build_toolbar_icon("strike"), "")
        self.strike_action.setCheckable(True)
        self.strike_action.setToolTip("Przekreślenie")

        toolbar.addSeparator()
        self.text_color_action = toolbar.addAction(self._build_toolbar_icon("text-color"), "")
        self.text_color_action.setToolTip("Kolor tekstu")
        self.highlight_action = toolbar.addAction(self._build_toolbar_icon("highlight"), "")
        self.highlight_action.setToolTip("Kolor podświetlenia")
        self.clear_format_action = toolbar.addAction(self._build_toolbar_icon("clear-format"), "")
        self.clear_format_action.setToolTip("Wyczyść formatowanie")

        toolbar.addSeparator()
        self.font_family_input = MenuSelectButton()
        self.font_family_input.setObjectName("FontFamilyButton")
        self.font_family_input.setMinimumWidth(220)
        for family in QtGui.QFontDatabase.families():
            self.font_family_input.addItem(family, family)
        toolbar.addWidget(self.font_family_input)

        self.font_size_input = MenuSelectButton()
        self.font_size_input.setObjectName("FontSizeButton")
        self.font_size_input.setMinimumWidth(72)
        for size in ("8", "9", "10", "11", "12", "13", "14", "16", "18", "20", "24", "28", "32", "36", "48"):
            self.font_size_input.addItem(size)
        toolbar.addWidget(self.font_size_input)
        self.decrease_font_size_action = toolbar.addAction(self._build_toolbar_icon("font-smaller"), "")
        self.decrease_font_size_action.setToolTip("Zmniejsz czcionkę")
        self.increase_font_size_action = toolbar.addAction(self._build_toolbar_icon("font-larger"), "")
        self.increase_font_size_action.setToolTip("Zwiększ czcionkę")

        toolbar.addSeparator()
        self.bulleted_list_action = toolbar.addAction(self._build_toolbar_icon("bulleted-list"), "")
        self.bulleted_list_action.setToolTip("Lista punktowana")
        self.numbered_list_action = toolbar.addAction(self._build_toolbar_icon("numbered-list"), "")
        self.numbered_list_action.setToolTip("Lista numerowana")
        self.decrease_indent_action = toolbar.addAction(self._build_toolbar_icon("outdent"), "")
        self.decrease_indent_action.setToolTip("Zmniejsz wcięcie")
        self.increase_indent_action = toolbar.addAction(self._build_toolbar_icon("indent"), "")
        self.increase_indent_action.setToolTip("Zwiększ wcięcie")

        toolbar.addSeparator()
        self.align_group = QtGui.QActionGroup(self)
        self.align_left_action = toolbar.addAction(self._build_toolbar_icon("align-left"), "")
        self.align_center_action = toolbar.addAction(self._build_toolbar_icon("align-center"), "")
        self.align_right_action = toolbar.addAction(self._build_toolbar_icon("align-right"), "")
        self.align_justify_action = toolbar.addAction(self._build_toolbar_icon("align-justify"), "")
        for action, tooltip in (
            (self.align_left_action, "Wyrównaj do lewej"),
            (self.align_center_action, "Wyśrodkuj"),
            (self.align_right_action, "Wyrównaj do prawej"),
            (self.align_justify_action, "Wyjustuj"),
        ):
            action.setCheckable(True)
            action.setToolTip(tooltip)
            self.align_group.addAction(action)

        toolbar._reflow()

        self.undo_action.triggered.connect(lambda: self.content_input.undo())
        self.redo_action.triggered.connect(lambda: self.content_input.redo())
        self.bold_action.triggered.connect(self._toggle_bold)
        self.italic_action.triggered.connect(self._toggle_italic)
        self.underline_action.triggered.connect(self._toggle_underline)
        self.strike_action.triggered.connect(self._toggle_strike)
        self.text_color_action.triggered.connect(self._choose_text_color)
        self.highlight_action.triggered.connect(self._choose_highlight_color)
        self.clear_format_action.triggered.connect(self._clear_selection_format)
        self.bulleted_list_action.triggered.connect(
            lambda: self._insert_list(QtGui.QTextListFormat.Style.ListDisc)
        )
        self.numbered_list_action.triggered.connect(
            lambda: self._insert_list(QtGui.QTextListFormat.Style.ListDecimal)
        )
        self.decrease_indent_action.triggered.connect(lambda: self._change_block_indent(-1))
        self.increase_indent_action.triggered.connect(lambda: self._change_block_indent(1))
        self.align_left_action.triggered.connect(
            lambda: self.content_input.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        )
        self.align_center_action.triggered.connect(
            lambda: self.content_input.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        )
        self.align_right_action.triggered.connect(
            lambda: self.content_input.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        )
        self.align_justify_action.triggered.connect(
            lambda: self.content_input.setAlignment(QtCore.Qt.AlignmentFlag.AlignJustify)
        )
        self.font_family_input.currentTextChanged.connect(self._set_font_family)
        self.font_size_input.currentTextChanged.connect(self._set_font_size)
        self.decrease_font_size_action.triggered.connect(lambda: self._adjust_font_size(-1))
        self.increase_font_size_action.triggered.connect(lambda: self._adjust_font_size(1))

    def _apply_visual_treatment(self) -> None:
        button_variants = {
            self.new_button: "primary",
            self.refresh_button: "subtle",
            self.import_images_button: "subtle",
            self.export_pdf_button: "subtle",
            self.pdf_preview_button: "subtle",
            self.transcribe_ai_button: "primary",
            self.trash_button: "link",
        }
        for button, variant in button_variants.items():
            button.setProperty("variant", variant)
            button.style().unpolish(button)
            button.style().polish(button)

        apply_card_shadow(self.save_button, blur_radius=14.0)

        apply_card_shadow(self.title_icon_tile, blur_radius=14.0)

    def _apply_translations(self) -> None:
        self.setWindowTitle(self._tr("app_title"))
        self.new_button.setText(self._tr("button_new_note"))
        self.export_pdf_button.setToolTip(self._tr("button_export_pdf"))
        self.save_button.setToolTip(self._tr("button_save"))
        self.settings_button.setToolTip(self._tr("sidebar_settings"))
        self.refresh_button.setText(self._tr("button_refresh"))
        self.import_images_button.setText("+")
        self.import_images_button.setToolTip(self._tr("button_import_images"))
        self.transcribe_ai_button.setText(self._tr("button_transcribe_ai"))
        self.saved_notes_label.setText(self._tr("label_saved_notes"))
        self.search_input.setPlaceholderText(self._tr("placeholder_search_notes"))
        self.trash_button.setText(self._tr("sidebar_trash"))
        self.attachments_header.setText(self._tr("label_images"))
        self.image_empty_label.setText(self._tr("label_no_images_added"))
        self.drag_hint.setText(self._tr("label_drag_hint"))
        self.image_order_hint.setText(self._tr("label_image_order_hint"))
        self.editor_title_label.setText(self._tr("label_note_content"))
        self.pdf_preview_button.setToolTip(self._tr("button_preview_pdf"))
        self.content_input.setPlaceholderText(self._tr("placeholder_note_content"))
        self.assistant_title_label.setText(self._tr("assistant_title"))
        self.assistant_mode_label.setText(self._tr("assistant_transcription_mode"))
        self.note_info_label.setText(self._tr("assistant_note_info"))
        self.info_created_label.setText(self._tr("assistant_created"))
        self.info_updated_label.setText(self._tr("assistant_updated"))
        self.info_images_label.setText(self._tr("assistant_images_count"))
        self.info_characters_label.setText(self._tr("assistant_characters_count"))
        self.tip_title_label.setText(self._tr("assistant_tip_title"))
        self.tip_text_label.setText(self._tr("assistant_tip_text"))
        self.loading_overlay.set_text(self._tr("loading_creating_note"))
        self.local_save_status_label.setText(self._tr("status_local_saved"))
        self.bold_action.setToolTip(self._tr("tooltip_bold"))
        self.italic_action.setToolTip(self._tr("tooltip_italic"))
        self.underline_action.setToolTip(self._tr("tooltip_underline"))
        self.strike_action.setToolTip(self._tr("tooltip_strike"))
        self.undo_action.setToolTip(self._tr("tooltip_undo"))
        self.redo_action.setToolTip(self._tr("tooltip_redo"))
        self.text_color_action.setToolTip(self._tr("tooltip_text_color"))
        self.highlight_action.setToolTip(self._tr("tooltip_highlight"))
        self.clear_format_action.setToolTip(self._tr("tooltip_clear_format"))
        self.bulleted_list_action.setToolTip(self._tr("tooltip_bulleted_list"))
        self.numbered_list_action.setToolTip(self._tr("tooltip_numbered_list"))
        self.decrease_indent_action.setToolTip(self._tr("tooltip_decrease_indent"))
        self.increase_indent_action.setToolTip(self._tr("tooltip_increase_indent"))
        self.decrease_font_size_action.setToolTip(self._tr("tooltip_decrease_font_size"))
        self.increase_font_size_action.setToolTip(self._tr("tooltip_increase_font_size"))
        self.align_left_action.setToolTip(self._tr("tooltip_align_left"))
        self.align_center_action.setToolTip(self._tr("tooltip_align_center"))
        self.align_right_action.setToolTip(self._tr("tooltip_align_right"))
        self.align_justify_action.setToolTip(self._tr("tooltip_align_justify"))
        self._rebuild_transcription_mode_button()
        self._update_note_count_badge()
        self._update_note_meta_label()
        self._update_character_count()
        self._update_assistant_panel()
        self._update_image_counter()
        self.image_empty_label.setVisible(self.image_list.count() == 0)

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

    def _update_note_count_badge(self) -> None:
        self.notes_count_label.setText(self._format_notes_count(self.note_list.count()))

    def _format_notes_count(self, count: int) -> str:
        if self.app_language == "pl":
            if count == 1:
                suffix = "notatka"
            elif count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
                suffix = "notatki"
            else:
                suffix = "notatek"
            return f"{count} {suffix}"

        suffix = "note" if count == 1 else "notes"
        return f"{count} {suffix}"

    def _update_note_meta_label(self) -> None:
        if self.current_note is None:
            self._set_note_meta_text(self._tr("note_meta_draft"), is_unsaved=True)
            return

        created_at = self._format_note_datetime(self.current_note.created_at)
        is_saved = self.repository.has_note(self.current_note.id)
        status = self._tr("note_meta_saved") if is_saved else self._tr("note_meta_unsaved")
        self._set_note_meta_text(
            self._tr("note_meta", created=created_at, status=status),
            is_unsaved=not is_saved,
            status=status,
        )

    def _mark_note_as_unsaved(self) -> None:
        if self.current_note is None:
            self._set_note_meta_text(self._tr("note_meta_draft"), is_unsaved=True)
            return

        created_at = self._format_note_datetime(self.current_note.created_at)
        status = self._tr("note_meta_unsaved")
        self._set_note_meta_text(
            self._tr("note_meta", created=created_at, status=status),
            is_unsaved=True,
            status=status,
        )

    def _set_note_meta_text(self, text: str, *, is_unsaved: bool, status: str | None = None) -> None:
        safe_text = escape(text)
        if is_unsaved:
            unsaved_text = status or self._tr("note_meta_unsaved")
            safe_unsaved_text = escape(unsaved_text)
            safe_unsaved_lower_text = escape(unsaved_text[:1].lower() + unsaved_text[1:])
            before_replace = safe_text
            safe_text = safe_text.replace(
                safe_unsaved_text,
                f'<span style="color:#1e3a8a; font-weight:700;">{safe_unsaved_text}</span>',
                1,
            )
            if safe_text == before_replace:
                safe_text = safe_text.replace(
                    safe_unsaved_lower_text,
                    f'<span style="color:#1e3a8a; font-weight:700;">{safe_unsaved_lower_text}</span>',
                    1,
                )
        self.note_meta_label.setText(safe_text)

    def _update_character_count(self) -> None:
        count = len(self.content_input.toPlainText()) if hasattr(self, "content_input") else 0
        if hasattr(self, "info_characters_value"):
            self.info_characters_value.setText(str(count))

    def _update_image_counter(self) -> None:
        total = self.image_list.count() if hasattr(self, "image_list") else 0
        for row in range(total):
            item = self.image_list.item(row)
            widget = self.image_list.itemWidget(item)
            if isinstance(widget, ImageThumbnailWidget):
                widget.set_selected(row == self.image_list.currentRow())

        if hasattr(self, "info_images_value"):
            self.info_images_value.setText(str(total))

    def _update_assistant_panel(self) -> None:
        if not hasattr(self, "assistant_mode_description"):
            return

        mode = self.transcription_mode_input.currentData() or "faithful"
        self.assistant_mode_description.setText(self._mode_description(str(mode)))

        if self.current_note is None:
            empty_value = self._tr("assistant_empty_value")
            self.info_created_value.setText(empty_value)
            self.info_updated_value.setText(empty_value)
        else:
            self.info_created_value.setText(
                self._format_note_datetime(self.current_note.created_at, include_time_for_past=False)
            )
            self.info_updated_value.setText(
                self._format_note_datetime(self.current_note.updated_at, include_time_for_past=False)
            )

        self._update_image_counter()

    def _mode_description(self, mode: str) -> str:
        return self._tr(f"mode_{mode}_description")

    def _format_note_datetime(self, value, *, include_time_for_past: bool = True) -> str:
        local_value = value.astimezone()
        today = datetime.now(local_value.tzinfo).date()
        if local_value.date() == today:
            prefix = "Dzisiaj" if self.app_language == "pl" else "Today"
            return f"{prefix}, {local_value.strftime('%H:%M')}"
        if not include_time_for_past:
            return local_value.strftime("%d.%m.%Y")
        return local_value.strftime("%d.%m.%Y, %H:%M")

    def _build_toolbar_icon(self, kind: str) -> QtGui.QIcon:
        pixmap = QtGui.QPixmap(24, 24)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        pen = QtGui.QPen(QtGui.QColor("#172b65"))
        pen.setWidthF(1.9)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        if kind == "bold":
            font = QtGui.QFont("DejaVu Sans", 13)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, "B")
        elif kind == "italic":
            font = QtGui.QFont("DejaVu Sans", 13)
            font.setItalic(True)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, "I")
        elif kind == "underline":
            font = QtGui.QFont("DejaVu Sans", 12)
            painter.setFont(font)
            painter.drawText(pixmap.rect().adjusted(0, -2, 0, 0), QtCore.Qt.AlignmentFlag.AlignCenter, "U")
            painter.drawLine(6, 18, 18, 18)
        elif kind == "strike":
            font = QtGui.QFont("DejaVu Sans", 12)
            painter.setFont(font)
            painter.drawText(pixmap.rect().adjusted(0, -1, 0, 0), QtCore.Qt.AlignmentFlag.AlignCenter, "S")
            painter.drawLine(6, 12, 18, 12)
        elif kind == "bulleted-list":
            painter.setBrush(QtGui.QColor("#172b65"))
            for y in (6, 12, 18):
                painter.drawEllipse(QtCore.QPointF(5, y), 1.5, 1.5)
                painter.drawLine(10, y, 19, y)
        elif kind == "numbered-list":
            font = QtGui.QFont("DejaVu Sans", 7)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QtCore.QRect(1, 3, 7, 7), QtCore.Qt.AlignmentFlag.AlignCenter, "1")
            painter.drawText(QtCore.QRect(1, 9, 7, 7), QtCore.Qt.AlignmentFlag.AlignCenter, "2")
            painter.drawText(QtCore.QRect(1, 15, 7, 7), QtCore.Qt.AlignmentFlag.AlignCenter, "3")
            for y in (6, 12, 18):
                painter.drawLine(10, y, 19, y)
        elif kind in {"align-left", "align-center", "align-right", "align-justify"}:
            line_widths = {
                "align-left": (15, 11, 15, 9),
                "align-center": (13, 17, 13, 17),
                "align-right": (15, 11, 15, 9),
                "align-justify": (16, 16, 16, 16),
            }[kind]
            y_positions = (6, 10, 14, 18)
            for width, y in zip(line_widths, y_positions):
                if kind == "align-center":
                    x1 = 12 - width / 2
                elif kind == "align-right":
                    x1 = 20 - width
                else:
                    x1 = 4
                painter.drawLine(QtCore.QPointF(x1, y), QtCore.QPointF(x1 + width, y))
        elif kind == "indent":
            painter.drawLine(10, 6, 20, 6)
            painter.drawLine(14, 12, 20, 12)
            painter.drawLine(10, 18, 20, 18)
            painter.drawLine(4, 9, 8, 12)
            painter.drawLine(4, 15, 8, 12)
        elif kind == "outdent":
            painter.drawLine(10, 6, 20, 6)
            painter.drawLine(14, 12, 20, 12)
            painter.drawLine(10, 18, 20, 18)
            painter.drawLine(8, 9, 4, 12)
            painter.drawLine(8, 15, 4, 12)
        elif kind == "undo":
            painter.drawLine(8, 7, 4, 11)
            painter.drawLine(8, 15, 4, 11)
            painter.drawArc(QtCore.QRectF(5, 7, 14, 10), 25 * 16, -245 * 16)
        elif kind == "redo":
            painter.drawLine(16, 7, 20, 11)
            painter.drawLine(16, 15, 20, 11)
            painter.drawArc(QtCore.QRectF(5, 7, 14, 10), 155 * 16, 245 * 16)
        elif kind == "text-color":
            font = QtGui.QFont("DejaVu Sans", 12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QtCore.QRect(4, 2, 16, 16), QtCore.Qt.AlignmentFlag.AlignCenter, "A")
            painter.setPen(QtGui.QPen(QtGui.QColor("#2563eb"), 3))
            painter.drawLine(6, 20, 18, 20)
        elif kind == "highlight":
            painter.setPen(QtGui.QPen(QtGui.QColor("#172b65"), 1.7))
            painter.drawRoundedRect(QtCore.QRectF(5, 5, 14, 11), 2, 2)
            painter.fillRect(QtCore.QRectF(7, 13, 10, 5), QtGui.QColor("#facc15"))
            painter.drawLine(7, 19, 17, 19)
        elif kind == "clear-format":
            font = QtGui.QFont("DejaVu Sans", 12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QtCore.QRect(3, 2, 14, 16), QtCore.Qt.AlignmentFlag.AlignCenter, "A")
            painter.drawLine(14, 16, 20, 20)
            painter.drawLine(20, 16, 14, 20)
        elif kind == "font-larger":
            font = QtGui.QFont("DejaVu Sans", 12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QtCore.QRect(3, 5, 13, 15), QtCore.Qt.AlignmentFlag.AlignCenter, "A")
            painter.drawLine(18, 17, 18, 7)
            painter.drawLine(14.5, 10.5, 18, 7)
            painter.drawLine(21.5, 10.5, 18, 7)
        elif kind == "font-smaller":
            font = QtGui.QFont("DejaVu Sans", 12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QtCore.QRect(3, 5, 13, 15), QtCore.Qt.AlignmentFlag.AlignCenter, "A")
            painter.drawLine(18, 7, 18, 17)
            painter.drawLine(14.5, 13.5, 18, 17)
            painter.drawLine(21.5, 13.5, 18, 17)
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

    def _toggle_strike(self) -> None:
        char_format = QtGui.QTextCharFormat()
        char_format.setFontStrikeOut(self.strike_action.isChecked())
        self._merge_char_format(char_format)

    def _choose_text_color(self) -> None:
        color = QtWidgets.QColorDialog.getColor(
            self.content_input.textColor(),
            self,
            self._tr("dialog_text_color"),
        )
        if not color.isValid():
            return

        char_format = QtGui.QTextCharFormat()
        char_format.setForeground(color)
        self._merge_char_format(char_format)

    def _choose_highlight_color(self) -> None:
        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor("#fff3a3"),
            self,
            self._tr("dialog_highlight_color"),
        )
        if not color.isValid():
            return

        char_format = QtGui.QTextCharFormat()
        char_format.setBackground(color)
        self._merge_char_format(char_format)

    def _clear_selection_format(self) -> None:
        cursor = self.content_input.textCursor()
        if not cursor.hasSelection():
            cursor.select(QtGui.QTextCursor.SelectionType.WordUnderCursor)

        clean_format = QtGui.QTextCharFormat()
        cursor.setCharFormat(clean_format)
        self.content_input.setTextCursor(cursor)
        self.content_input.setCurrentCharFormat(clean_format)

    def _change_block_indent(self, delta: int) -> None:
        cursor = self.content_input.textCursor()
        cursor.beginEditBlock()
        block_format = cursor.blockFormat()
        block_format.setIndent(max(0, block_format.indent() + delta))
        cursor.setBlockFormat(block_format)
        cursor.endEditBlock()
        self.content_input.setTextCursor(cursor)

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

    def _adjust_font_size(self, delta: int) -> None:
        current_format = self.content_input.currentCharFormat()
        current_size = (
            current_format.fontPointSize()
            or self.content_input.fontPointSize()
            or self.content_input.font().pointSizeF()
            or 12
        )
        next_size = max(1, current_size + delta)
        char_format = QtGui.QTextCharFormat()
        char_format.setFontPointSize(next_size)
        self._merge_char_format(char_format)
        self._updating_format_controls = True
        self.font_size_input.setCurrentText(str(int(next_size)))
        self._updating_format_controls = False

    def _sync_format_controls(self) -> None:
        if not hasattr(self, "content_input"):
            return

        self._updating_format_controls = True
        char_format = self.content_input.currentCharFormat()
        font = char_format.font()
        self.bold_action.setChecked(font.bold())
        self.italic_action.setChecked(font.italic())
        self.underline_action.setChecked(font.underline())
        self.strike_action.setChecked(font.strikeOut())
        alignment = self.content_input.alignment()
        self.align_left_action.setChecked(bool(alignment & QtCore.Qt.AlignmentFlag.AlignLeft))
        self.align_center_action.setChecked(bool(alignment & QtCore.Qt.AlignmentFlag.AlignHCenter))
        self.align_right_action.setChecked(bool(alignment & QtCore.Qt.AlignmentFlag.AlignRight))
        self.align_justify_action.setChecked(bool(alignment & QtCore.Qt.AlignmentFlag.AlignJustify))
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
        self._update_note_count_badge()
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
        search_text = ""
        if hasattr(self, "search_input"):
            search_text = self.search_input.text().strip().lower()

        for note in notes:
            if search_text and search_text not in note.display_title.lower():
                continue

            note_time = note.updated_at.astimezone().strftime("%d.%m.%Y, %H:%M")
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.ItemDataRole.UserRole, note.id)
            item.setToolTip(note.updated_at.astimezone().strftime("%Y-%m-%d %H:%M"))
            item.setSizeHint(QtCore.QSize(220, 62))
            self.note_list.addItem(item)
            widget = NoteListItemWidget(note, note_time, self.note_list)
            widget.selectedRequested.connect(self._select_note)
            widget.trashRequested.connect(self._move_note_to_trash_from_list)
            self.note_list.setItemWidget(item, widget)
        self._sync_note_list_widget_selection()

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

    def _delete_current_note(self) -> None:
        if self.current_note is None:
            return

        note_title = self.current_note.display_title
        if not self.repository.has_note(self.current_note.id):
            self._create_new_note()
            self.statusBar().showMessage(self._tr("status_cleared_draft"))
            return

        message_box = QtWidgets.QMessageBox(self)
        message_box.setWindowTitle(self._tr("dialog_delete_note_title"))
        message_box.setText(self._tr("dialog_delete_note_text", title=note_title))
        delete_button = message_box.addButton(
            self._tr("dialog_delete_note_confirm"),
            QtWidgets.QMessageBox.ButtonRole.DestructiveRole,
        )
        cancel_button = message_box.addButton(
            self._tr("dialog_cancel"),
            QtWidgets.QMessageBox.ButtonRole.RejectRole,
        )
        message_box.exec()

        if message_box.clickedButton() != delete_button or message_box.clickedButton() == cancel_button:
            return

        self.repository.move_to_trash(self.current_note.id)
        self.current_note = None
        self.refresh_notes()
        self._create_new_note()
        self.statusBar().showMessage(self._tr("status_deleted_note", title=note_title))

    def _move_note_to_trash_from_list(self, note_id: str) -> None:
        if not self.repository.has_note(note_id):
            return

        note = self.repository.get_note(note_id)
        self.repository.move_to_trash(note_id)

        if self.current_note is not None and self.current_note.id == note_id:
            self.current_note = None
            self._create_new_note()

        self.refresh_notes()
        self.statusBar().showMessage(self._tr("status_moved_note_to_trash", title=note.display_title))

    def _open_trash_dialog(self) -> None:
        dialog = TrashDialog(self.repository, self._tr, self)
        dialog.exec()
        if dialog.changed:
            self.refresh_notes(selected_note_id=self.current_note.id if self.current_note else None)
            self.statusBar().showMessage(self._tr("status_trash_updated"))

    def _select_note(self, note_id: str) -> None:
        for row in range(self.note_list.count()):
            item = self.note_list.item(row)
            if item.data(QtCore.Qt.ItemDataRole.UserRole) == note_id:
                self.note_list.setCurrentItem(item)
                self._sync_note_list_widget_selection()
                return

    def _sync_note_list_widget_selection(self) -> None:
        for row in range(self.note_list.count()):
            item = self.note_list.item(row)
            widget = self.note_list.itemWidget(item)
            if isinstance(widget, NoteListItemWidget):
                widget.set_selected(item.isSelected())

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

    def _reorder_image_to_index(self, relative_path: str, insert_index: int) -> None:
        if self.current_note is None or relative_path not in self.current_note.image_paths:
            return

        self._sync_form_to_current_note()
        image_paths = list(self.current_note.image_paths)
        image_paths.remove(relative_path)
        bounded_index = max(0, min(insert_index, len(image_paths)))
        image_paths.insert(bounded_index, relative_path)
        self.current_note.image_paths = image_paths
        self.repository.save(self.current_note)

        self._refresh_image_list()
        self._select_image(relative_path)
        self.refresh_notes(selected_note_id=self.current_note.id)
        self.statusBar().showMessage(self._tr("status_changed_image_order"))

    def _reorder_image_near_target(
        self, source_path: str, target_path: str, insert_after_target: bool
    ) -> None:
        if self.current_note is None:
            return
        if source_path not in self.current_note.image_paths or target_path not in self.current_note.image_paths:
            return

        image_paths = list(self.current_note.image_paths)
        image_paths.remove(source_path)
        target_index = image_paths.index(target_path)
        insert_index = target_index + 1 if insert_after_target else target_index
        self._reorder_image_to_index(source_path, insert_index)

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
                app_language=dialog.app_language,
            )
        except OSError as error:
            QtWidgets.QMessageBox.warning(
                self,
                self._tr("dialog_save_settings_error"),
                f"{self._tr('dialog_save_settings_error')}: {error}",
            )
            return

        self.app_config = load_app_config(base_dir=self.repository.base_dir)
        self.app_language = (
            self.app_config.app_language if self.app_config.app_language in {"pl", "en"} else "pl"
        )
        self.ai_provider = GeminiAIProvider(
            api_key=self.app_config.gemini_api_key,
            model_name=self.app_config.gemini_model,
            config_path=self.app_config.config_path,
        )
        self._apply_translations()
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
                self._current_pdf_payload(),
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

    def _open_current_note_pdf_preview(self) -> None:
        if self.current_note is None:
            self.current_note = Note.create_empty()
            self.current_note.title = self._tr("default_note_title")

        self._sync_form_to_current_note()
        temp_file = tempfile.NamedTemporaryFile(prefix="ink2text-preview-", suffix=".pdf", delete=False)
        temp_path = Path(temp_file.name)
        temp_file.close()

        try:
            export_note_to_pdf(temp_path, self._current_pdf_payload())
            dialog = PDFPreviewDialog(temp_path, self._tr("dialog_pdf_preview"), self)
        except RuntimeError as error:
            temp_path.unlink(missing_ok=True)
            QtWidgets.QMessageBox.warning(self, self._tr("dialog_export_error"), str(error))
            self.statusBar().showMessage(self._tr("status_pdf_preview_failed"))
            return
        except OSError as error:
            temp_path.unlink(missing_ok=True)
            QtWidgets.QMessageBox.warning(
                self,
                self._tr("dialog_save_error"),
                f"{self._tr('dialog_save_error')}: {error}",
            )
            self.statusBar().showMessage(self._tr("status_pdf_preview_failed"))
            return

        dialog.showMaximized()
        dialog.exec()

    def _current_pdf_payload(self) -> PDFExportPayload:
        if self.current_note is None:
            return PDFExportPayload(title="", content="")

        return PDFExportPayload(
            title=self.current_note.title,
            content=self.current_note.content,
            content_html=(self.current_note.content if self.current_note.content_format == "html" else None),
        )

    def _refresh_image_list(self) -> None:
        self.image_list.clear()
        self._update_image_counter()

        if self.current_note is None:
            self.image_empty_label.setVisible(True)
            self._update_assistant_panel()
            return

        for relative_path in self.current_note.image_paths:
            image_path = self.repository.resolve_image_path(relative_path)
            item = QtWidgets.QListWidgetItem()
            item.setData(QtCore.Qt.ItemDataRole.UserRole, relative_path)
            item.setToolTip(relative_path)
            item.setSizeHint(QtCore.QSize(158, 122))
            self.image_list.addItem(item)

            widget = ImageThumbnailWidget(relative_path, image_path, self.image_list)
            widget.selectedRequested.connect(self._select_image)
            widget.previewRequested.connect(self._open_image_preview)
            widget.removeRequested.connect(self._remove_image_by_relative_path)
            widget.reorderRequested.connect(self._reorder_image_near_target)
            self.image_list.setItemWidget(item, widget)

        self.image_empty_label.setVisible(self.image_list.count() == 0)
        if self.image_list.count() > 0:
            self.image_list.setCurrentRow(0)
        self._update_assistant_panel()

    def _update_image_preview(self) -> None:
        self._update_image_counter()

    def _open_image_preview(self, relative_path: str) -> None:
        self._select_image(relative_path)
        image_path = self.repository.resolve_image_path(relative_path)
        dialog = ImagePreviewDialog(image_path, Path(relative_path).name, self)
        dialog.exec()

    def _remove_image_by_relative_path(self, relative_path: str) -> None:
        if self.current_note is None:
            return

        self._sync_form_to_current_note()
        self.repository.remove_image(self.current_note, relative_path)
        self._refresh_image_list()
        self.refresh_notes(selected_note_id=self.current_note.id)
        self.statusBar().showMessage(self._tr("status_removed_image"))

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
        self.title_input.blockSignals(True)
        self.title_input.setText(note.title)
        self.title_input.blockSignals(False)
        self.content_input.blockSignals(True)
        if note.content.strip():
            if note.content_format == "html":
                self.content_input.setHtml(convert_note_content_to_editor_html(note.content, "html"))
            else:
                self.content_input.setHtml(
                    convert_note_content_to_editor_html(note.content, note.content_format)
                )
        else:
            self.content_input.clear()
        self.content_input.blockSignals(False)
        self._refresh_image_list()
        self._sync_format_controls()
        self._update_note_meta_label()
        self._update_character_count()
        self._update_assistant_panel()

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
        if is_busy:
            self.loading_overlay.start()
        else:
            self.loading_overlay.stop()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "loading_overlay") and self.centralWidget() is not None:
            self.loading_overlay.setGeometry(self.centralWidget().rect())
