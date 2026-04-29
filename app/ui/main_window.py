from __future__ import annotations

from html import escape
from pathlib import Path
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


class ImageThumbnailWidget(QtWidgets.QFrame):
    previewRequested = QtCore.Signal(str)
    removeRequested = QtCore.Signal(str)

    def __init__(self, relative_path: str, image_path: Path, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.relative_path = relative_path
        self.image_path = image_path
        self.setObjectName("ImageThumbnailWidget")
        self.setMouseTracking(True)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.image_label = QtWidgets.QLabel()
        self.image_label.setObjectName("ThumbnailImage")
        self.image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(142, 106)
        self.image_label.setPixmap(self._thumbnail_pixmap())

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

    def enterEvent(self, event: QtCore.QEvent) -> None:
        self.trash_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self.trash_button.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self.previewRequested.emit(self.relative_path)
        super().mousePressEvent(event)

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
        center = rect.center()
        gradient = QtGui.QConicalGradient(center, -self._angle)
        gradient.setColorAt(0.00, QtGui.QColor(23, 43, 101, 15))
        gradient.setColorAt(0.45, QtGui.QColor(30, 58, 138, 90))
        gradient.setColorAt(0.82, QtGui.QColor(30, 58, 138, 230))
        gradient.setColorAt(1.00, QtGui.QColor(30, 58, 138, 255))

        pen = QtGui.QPen(QtGui.QBrush(gradient), 9)
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
        self.image_list = QtWidgets.QListWidget()
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
        self.logo_mark = QtWidgets.QLabel("✦")
        self.logo_mark.setObjectName("LogoMark")
        self.logo_mark.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
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
        self.trash_button.setIcon(build_simple_icon("trash", "#7b879d", 32))
        self.trash_button.setIconSize(QtCore.QSize(18, 18))
        self.sidebar_settings_button = QtWidgets.QPushButton("Ustawienia")
        self.sidebar_settings_button.setObjectName("SidebarLinkButton")
        self.sidebar_settings_button.setIcon(build_simple_icon("settings", "#7b879d", 32))
        self.sidebar_settings_button.setIconSize(QtCore.QSize(18, 18))
        sidebar_layout.addWidget(self.trash_button)
        sidebar_layout.addWidget(self.sidebar_settings_button)

        main_area = QtWidgets.QWidget()
        main_area.setObjectName("MainArea")
        main_layout = QtWidgets.QVBoxLayout(main_area)
        main_layout.setContentsMargins(18, 18, 18, 14)
        main_layout.setSpacing(14)

        self.top_bar = QtWidgets.QFrame()
        self.top_bar.setObjectName("TopBar")
        top_layout = QtWidgets.QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(18, 10, 18, 10)
        top_layout.setSpacing(14)

        title_shell = QtWidgets.QHBoxLayout()
        title_shell.setSpacing(14)
        self.title_icon_tile = QtWidgets.QLabel()
        self.title_icon_tile.setObjectName("TitleIconTile")
        self.title_icon_tile.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.title_icon_tile.setPixmap(build_simple_icon("edit", "#172b65", 32).pixmap(24, 24))
        self.title_icon_tile.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.title_icon_tile.installEventFilter(self)
        title_shell.addWidget(self.title_icon_tile, alignment=QtCore.Qt.AlignmentFlag.AlignTop)

        title_area = QtWidgets.QVBoxLayout()
        title_area.setSpacing(2)
        title_row = QtWidgets.QHBoxLayout()
        title_row.setSpacing(8)
        self.title_input = QtWidgets.QLineEdit()
        self.title_input.setObjectName("TitleInput")
        self.title_input.setClearButtonEnabled(False)
        self.note_meta_label = QtWidgets.QLabel()
        self.note_meta_label.setObjectName("MetaText")
        self.note_meta_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        title_row.addWidget(self.title_input)
        title_row.addStretch()
        title_area.addLayout(title_row)
        title_area.addWidget(self.note_meta_label)
        title_shell.addLayout(title_area, stretch=1)
        top_layout.addLayout(title_shell, stretch=1)

        self.save_button = QtWidgets.QPushButton("Zapisz")
        self.save_button.setObjectName("TopActionButton")
        self.save_button.setIcon(build_simple_icon("save", "#172b65", 32))
        self.save_button.setIconSize(QtCore.QSize(24, 24))
        self.export_pdf_button = QtWidgets.QPushButton("Eksportuj PDF")
        self.export_pdf_button.setObjectName("TopActionButton")
        self.export_pdf_button.setIcon(build_simple_icon("pdf", "#172b65", 32))
        self.export_pdf_button.setIconSize(QtCore.QSize(24, 24))
        self.refresh_button = QtWidgets.QPushButton("Odśwież")
        top_layout.addWidget(self.save_button)
        top_layout.addWidget(self.export_pdf_button)

        content_row = QtWidgets.QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(14)

        center_column = QtWidgets.QVBoxLayout()
        center_column.setContentsMargins(0, 0, 0, 0)
        center_column.setSpacing(14)

        self.photos_card = QtWidgets.QFrame()
        self.photos_card.setObjectName("ContentCard")
        photos_layout = QtWidgets.QVBoxLayout(self.photos_card)
        photos_layout.setContentsMargins(18, 16, 18, 16)
        photos_layout.setSpacing(10)

        photos_header = QtWidgets.QHBoxLayout()
        photos_header.setSpacing(12)
        self.attachments_header = QtWidgets.QLabel()
        self.attachments_header.setObjectName("CardTitle")
        self.import_images_button = QtWidgets.QPushButton("+")
        self.import_images_button.setObjectName("AddImageButton")
        self.move_image_earlier_button = QtWidgets.QPushButton("‹")
        self.move_image_earlier_button.setObjectName("IconButton")
        self.move_image_later_button = QtWidgets.QPushButton("›")
        self.move_image_later_button.setObjectName("IconButton")
        self.image_count_label = QtWidgets.QLabel("0 / 0")
        self.image_count_label.setObjectName("ImageCounter")
        photos_header.addWidget(self.attachments_header)
        photos_header.addWidget(self.import_images_button)
        photos_header.addStretch()
        photos_header.addWidget(self.move_image_earlier_button)
        photos_header.addWidget(self.image_count_label)
        photos_header.addWidget(self.move_image_later_button)
        photos_layout.addLayout(photos_header)

        self.image_empty_label = QtWidgets.QLabel()
        self.image_empty_label.setObjectName("ThumbnailEmpty")
        self.image_empty_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.image_empty_label.setWordWrap(True)
        photos_layout.addWidget(self.image_empty_label)

        self.image_list = QtWidgets.QListWidget()
        self.image_list.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        self.image_list.setFlow(QtWidgets.QListView.Flow.LeftToRight)
        self.image_list.setWrapping(True)
        self.image_list.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.image_list.setMovement(QtWidgets.QListView.Movement.Static)
        self.image_list.setGridSize(QtCore.QSize(164, 132))
        self.image_list.setSpacing(12)
        self.image_list.setObjectName("ImageList")
        self.image_list.setMinimumHeight(170)
        photos_layout.addWidget(self.image_list)

        self.drag_hint = QtWidgets.QLabel()
        self.drag_hint.setObjectName("HelperText")
        photos_layout.addWidget(self.drag_hint)

        self.editor_section = QtWidgets.QFrame()
        self.editor_section.setObjectName("ContentCard")
        editor_layout = QtWidgets.QVBoxLayout(self.editor_section)
        editor_layout.setContentsMargins(18, 16, 18, 16)
        editor_layout.setSpacing(10)

        editor_header = QtWidgets.QHBoxLayout()
        editor_header.setSpacing(12)
        self.editor_title_label = QtWidgets.QLabel()
        self.editor_title_label.setObjectName("CardTitle")
        editor_header.addWidget(self.editor_title_label)
        editor_header.addStretch()
        editor_layout.addLayout(editor_header)

        self._build_editor_toolbar()
        editor_layout.addWidget(self.editor_toolbar)

        self.content_input = QtWidgets.QTextEdit()
        self.content_input.setAcceptRichText(True)
        self.content_input.setObjectName("ContentEditor")
        self.content_input.setMinimumHeight(260)
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
        self.sidebar_settings_button.clicked.connect(self._open_ai_settings)
        self.trash_button.clicked.connect(self._open_trash_dialog)
        self.move_image_earlier_button.clicked.connect(lambda: self._move_selected_image(-1))
        self.move_image_later_button.clicked.connect(lambda: self._move_selected_image(1))
        self.note_list.itemSelectionChanged.connect(self._load_selected_note)
        self.image_list.itemSelectionChanged.connect(self._update_image_counter)
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
        toolbar = QtWidgets.QToolBar("Formatowanie")
        toolbar.setObjectName("EditorToolbar")
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
        self.font_family_input.setObjectName("FontFamilyButton")
        self.font_family_input.setMinimumWidth(220)
        for family in QtGui.QFontDatabase.families():
            self.font_family_input.addItem(family, family)
        toolbar.addWidget(self.font_family_input)

        self.font_size_input = MenuSelectButton()
        self.font_size_input.setObjectName("FontSizeButton")
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

    def _apply_visual_treatment(self) -> None:
        button_variants = {
            self.new_button: "primary",
            self.refresh_button: "subtle",
            self.import_images_button: "subtle",
            self.transcribe_ai_button: "primary",
            self.sidebar_settings_button: "link",
            self.trash_button: "link",
            self.move_image_earlier_button: "subtle",
            self.move_image_later_button: "subtle",
        }
        for button, variant in button_variants.items():
            button.setProperty("variant", variant)
            button.style().unpolish(button)
            button.style().polish(button)

        for button in (self.save_button, self.export_pdf_button):
            apply_card_shadow(button, blur_radius=16.0)

        apply_card_shadow(self.title_icon_tile, blur_radius=14.0)

        for widget in (self.photos_card, self.editor_section, self.assistant_panel):
            apply_card_shadow(widget, blur_radius=18.0)

    def _apply_translations(self) -> None:
        self.setWindowTitle(self._tr("app_title"))
        self.new_button.setText(self._tr("button_new_note"))
        self.export_pdf_button.setText(self._tr("button_export_pdf"))
        self.save_button.setText(self._tr("button_save"))
        self.refresh_button.setText(self._tr("button_refresh"))
        self.import_images_button.setText("+")
        self.import_images_button.setToolTip(self._tr("button_import_images"))
        self.transcribe_ai_button.setText(self._tr("button_transcribe_ai"))
        self.saved_notes_label.setText(self._tr("label_saved_notes"))
        self.search_input.setPlaceholderText(self._tr("placeholder_search_notes"))
        self.trash_button.setText(self._tr("sidebar_trash"))
        self.sidebar_settings_button.setText(self._tr("sidebar_settings"))
        self.attachments_header.setText(self._tr("label_images"))
        self.move_image_earlier_button.setToolTip(self._tr("button_move_earlier"))
        self.move_image_later_button.setToolTip(self._tr("button_move_later"))
        self.image_empty_label.setText(self._tr("label_no_images_added"))
        self.drag_hint.setText(self._tr("label_drag_hint"))
        self.editor_title_label.setText(self._tr("label_note_content"))
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
        self.bulleted_list_action.setToolTip(self._tr("tooltip_bulleted_list"))
        self.numbered_list_action.setToolTip(self._tr("tooltip_numbered_list"))
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
        selected = self.image_list.currentRow() + 1 if total and self.image_list.currentRow() >= 0 else 0
        self.image_count_label.setText(self._tr("image_counter", current=selected, total=total))

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
            self.info_created_value.setText(self._format_note_datetime(self.current_note.created_at))
            self.info_updated_value.setText(self._format_note_datetime(self.current_note.updated_at))

        self._update_image_counter()

    def _mode_description(self, mode: str) -> str:
        return self._tr(f"mode_{mode}_description")

    def _format_note_datetime(self, value) -> str:
        local_value = value.astimezone()
        today = datetime.now(local_value.tzinfo).date()
        if local_value.date() == today:
            prefix = "Dzisiaj" if self.app_language == "pl" else "Today"
            return f"{prefix}, {local_value.strftime('%H:%M')}"
        return local_value.strftime("%d.%m.%Y, %H:%M")

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
            item.setSizeHint(QtCore.QSize(158, 128))
            self.image_list.addItem(item)

            widget = ImageThumbnailWidget(relative_path, image_path, self.image_list)
            widget.previewRequested.connect(self._open_image_preview)
            widget.removeRequested.connect(self._remove_image_by_relative_path)
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
