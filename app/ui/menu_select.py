from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


class MenuSelectButton(QtWidgets.QPushButton):
    currentIndexChanged = QtCore.Signal(int)
    currentTextChanged = QtCore.Signal(str)
    currentDataChanged = QtCore.Signal(object)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[tuple[str, object]] = []
        self._current_index = -1
        self._placeholder_text = "Wybierz"
        self._popup = QtWidgets.QFrame(None, QtCore.Qt.WindowType.Popup)
        self._popup.setObjectName("SelectPopup")
        self._popup.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)
        popup_layout = QtWidgets.QVBoxLayout(self._popup)
        popup_layout.setContentsMargins(6, 6, 6, 6)
        popup_layout.setSpacing(0)

        self._list_widget = QtWidgets.QListWidget(self._popup)
        self._list_widget.setObjectName("SelectPopupList")
        self._list_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_widget.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        popup_layout.addWidget(self._list_widget)

        self.setProperty("selectMenu", True)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._toggle_popup)
        self._list_widget.itemClicked.connect(self._select_popup_item)
        self._update_button_label()

    def addItem(self, text: str, data: object | None = None) -> None:
        item_index = len(self._items)
        item_data = text if data is None else data
        self._items.append((text, item_data))
        item = QtWidgets.QListWidgetItem(text)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, item_index)
        item.setSizeHint(QtCore.QSize(0, 34))
        self._list_widget.addItem(item)
        if self._current_index < 0:
            self.setCurrentIndex(0)

    def addItems(self, texts: list[str]) -> None:
        for text in texts:
            self.addItem(text, text)

    def clear(self) -> None:
        self._list_widget.clear()
        self._items.clear()
        self._current_index = -1
        self._update_button_label()

    def setPlaceholderText(self, text: str) -> None:
        self._placeholder_text = text
        self._update_button_label()

    def count(self) -> int:
        return len(self._items)

    def currentIndex(self) -> int:
        return self._current_index

    def currentText(self) -> str:
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index][0]
        return ""

    def currentData(self):
        if 0 <= self._current_index < len(self._items):
            return self._items[self._current_index][1]
        return None

    def findText(self, text: str) -> int:
        for index, (item_text, _item_data) in enumerate(self._items):
            if item_text == text:
                return index
        return -1

    def findData(self, data: object) -> int:
        for index, (_item_text, item_data) in enumerate(self._items):
            if item_data == data:
                return index
        return -1

    def setCurrentIndex(self, index: int) -> None:
        if index < 0 or index >= len(self._items):
            return

        changed = index != self._current_index
        self._current_index = index
        self._sync_checked_item()
        self._update_button_label()

        if changed:
            self.currentIndexChanged.emit(index)
            self.currentTextChanged.emit(self.currentText())
            self.currentDataChanged.emit(self.currentData())

    def setCurrentText(self, text: str) -> None:
        index = self.findText(text)
        if index >= 0:
            self.setCurrentIndex(index)

    def setCurrentData(self, data: object) -> None:
        index = self.findData(data)
        if index >= 0:
            self.setCurrentIndex(index)

    def _sync_checked_item(self) -> None:
        for index in range(self._list_widget.count()):
            item = self._list_widget.item(index)
            font = item.font()
            font.setWeight(QtGui.QFont.Weight.DemiBold if index == self._current_index else QtGui.QFont.Weight.Normal)
            item.setFont(font)
            item.setSelected(index == self._current_index)
        if self._current_index >= 0:
            self._list_widget.setCurrentRow(self._current_index)

    def _update_button_label(self) -> None:
        text = self.currentText() or self._placeholder_text
        self.setText(f"   {text}")

    def _toggle_popup(self) -> None:
        if self._popup.isVisible():
            self._popup.hide()
            return
        self._show_popup()

    def _show_popup(self) -> None:
        if not self._items:
            return

        self._sync_checked_item()
        screen = self.screen() or QtWidgets.QApplication.primaryScreen()
        available_geometry = screen.availableGeometry() if screen is not None else QtCore.QRect()
        row_height = 34
        visible_rows = min(max(self._list_widget.count(), 1), 9)
        popup_height = min(360, visible_rows * row_height + 14)
        content_width = self._list_widget.sizeHintForColumn(0) + 44
        popup_width = max(self.width(), min(max(content_width, 180), 340))

        bottom_left = self.mapToGlobal(QtCore.QPoint(0, self.height() + 4))
        top_left = QtCore.QPoint(bottom_left)
        if available_geometry.isValid() and bottom_left.y() + popup_height > available_geometry.bottom():
            top_left.setY(self.mapToGlobal(QtCore.QPoint(0, -popup_height - 4)).y())
        if available_geometry.isValid() and top_left.x() + popup_width > available_geometry.right():
            top_left.setX(max(available_geometry.left(), available_geometry.right() - popup_width))

        self._popup.setGeometry(QtCore.QRect(top_left, QtCore.QSize(popup_width, popup_height)))
        self._popup.show()
        self._list_widget.setFocus(QtCore.Qt.FocusReason.PopupFocusReason)
        if self._current_index >= 0:
            self._list_widget.scrollToItem(
                self._list_widget.item(self._current_index),
                QtWidgets.QAbstractItemView.ScrollHint.PositionAtCenter,
            )

    def _select_popup_item(self, item: QtWidgets.QListWidgetItem) -> None:
        index = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if isinstance(index, int):
            self.setCurrentIndex(index)
        self._popup.hide()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        pen = QtGui.QPen(QtGui.QColor("#66728a"), 1.8)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        center_y = self.height() / 2 + 1
        right = self.width() - 18
        painter.drawLine(QtCore.QPointF(right - 5, center_y - 2), QtCore.QPointF(right, center_y + 3))
        painter.drawLine(QtCore.QPointF(right, center_y + 3), QtCore.QPointF(right + 5, center_y - 2))
