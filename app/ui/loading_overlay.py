from __future__ import annotations

import math

from PySide6 import QtCore, QtGui, QtWidgets


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
