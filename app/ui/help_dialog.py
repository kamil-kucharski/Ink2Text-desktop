from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from app.ui.icons import build_simple_icon


class HelpTipsButton(QtWidgets.QFrame):
    clicked = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("HelpTipsButton")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)

        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setObjectName("HelpTipsIcon")
        self.icon_label.setPixmap(build_simple_icon("question", "#7b879d", 28).pixmap(20, 20))
        self.text_label = QtWidgets.QLabel()
        self.text_label.setObjectName("HelpTipsText")
        self.arrow_label = QtWidgets.QLabel()
        self.arrow_label.setObjectName("HelpTipsArrow")
        self.arrow_label.setPixmap(build_simple_icon("arrow-right", "#7b879d", 28).pixmap(20, 20))

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label, stretch=1)
        layout.addWidget(self.arrow_label)

    def setText(self, text: str) -> None:  # noqa: N802 - Qt-style API for consistency
        self.text_label.setText(text)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class HelpDialog(QtWidgets.QDialog):
    def __init__(self, translator, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._tr = translator
        self.setWindowTitle(self._tr("help_dialog_title"))
        self.resize(700, 680)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(16)

        header = QtWidgets.QHBoxLayout()
        header.setSpacing(14)
        icon_tile = QtWidgets.QLabel()
        icon_tile.setObjectName("HelpDialogIconTile")
        icon_tile.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        icon_tile.setPixmap(build_simple_icon("question", "#172b65", 34).pixmap(26, 26))
        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(4)
        title = QtWidgets.QLabel(self._tr("help_dialog_title"))
        title.setObjectName("DialogTitle")
        subtitle = QtWidgets.QLabel(self._tr("help_dialog_subtitle"))
        subtitle.setObjectName("DialogSubtitle")
        subtitle.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addWidget(icon_tile)
        header.addLayout(title_box, stretch=1)
        layout.addLayout(header)

        steps_layout = QtWidgets.QVBoxLayout()
        steps_layout.setSpacing(10)
        for number in range(1, 6):
            steps_layout.addWidget(
                self._build_step_card(
                    number,
                    self._tr(f"help_step_{number}_title"),
                    self._tr(f"help_step_{number}_text"),
                )
            )
        layout.addLayout(steps_layout)

        close_button = QtWidgets.QPushButton(self._tr("dialog_close"))
        close_button.setObjectName("DialogCloseButton")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

    def _build_step_card(self, number: int, title: str, text: str) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setObjectName("HelpStepCard")
        card.setMinimumHeight(86)
        card.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        layout = QtWidgets.QHBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        number_label = QtWidgets.QLabel(str(number))
        number_label.setObjectName("HelpStepNumber")
        number_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(3)
        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("HelpStepTitle")
        body_label = QtWidgets.QLabel(text)
        body_label.setObjectName("HelpStepText")
        body_label.setWordWrap(True)
        body_label.setMinimumHeight(body_label.fontMetrics().lineSpacing() * 2 + 8)
        body_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        text_layout.addWidget(title_label)
        text_layout.addWidget(body_label)

        layout.addWidget(number_label)
        layout.addLayout(text_layout, stretch=1)
        return card
