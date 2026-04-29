from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class MenuSelectButton(QtWidgets.QPushButton):
    currentIndexChanged = QtCore.Signal(int)
    currentTextChanged = QtCore.Signal(str)
    currentDataChanged = QtCore.Signal(object)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[tuple[str, object]] = []
        self._actions: list[QtWidgets.QAction] = []
        self._current_index = -1
        self._menu = QtWidgets.QMenu(self)
        self.setMenu(self._menu)
        self.setStyleSheet("text-align: left; padding-right: 18px;")
        self._update_button_label()

    def addItem(self, text: str, data: object | None = None) -> None:
        item_index = len(self._items)
        item_data = text if data is None else data
        self._items.append((text, item_data))
        action = self._menu.addAction(text)
        action.setCheckable(True)
        action.triggered.connect(lambda _checked=False, index=item_index: self.setCurrentIndex(index))
        self._actions.append(action)
        if self._current_index < 0:
            self.setCurrentIndex(0)

    def addItems(self, texts: list[str]) -> None:
        for text in texts:
            self.addItem(text, text)

    def clear(self) -> None:
        self._menu.clear()
        self._items.clear()
        self._actions.clear()
        self._current_index = -1
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
        self._sync_checked_action()
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

    def _sync_checked_action(self) -> None:
        for index, action in enumerate(self._actions):
            action.setChecked(index == self._current_index)

    def _update_button_label(self) -> None:
        text = self.currentText() or "Wybierz"
        self.setText(f"{text}  v")
