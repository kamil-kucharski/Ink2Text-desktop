from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from app.ui.icons import build_simple_icon


IMAGE_REORDER_MIME = "application/x-ink2text-image-path"


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
        close_text: str = "Zamknij",
        load_error_text: str = "Nie udało się wczytać podglądu",
    ) -> None:
        super().__init__(parent)
        self.image_path = image_path
        self.original_pixmap = QtGui.QPixmap(str(image_path))
        self.load_error_text = load_error_text
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

        close_button = QtWidgets.QPushButton(close_text)
        close_button.setObjectName("DialogCloseButton")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        self._update_preview()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._update_preview()

    def _update_preview(self) -> None:
        if self.original_pixmap.isNull():
            self.image_label.setText(self.load_error_text)
            return

        self.image_label.setPixmap(
            self.original_pixmap.scaled(
                self.image_label.size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        )
