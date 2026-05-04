from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


class ResponsiveEditorToolbar(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[QtWidgets.QWidget] = []
        self._actions: list[QtGui.QAction] = []
        self._icon_size = QtCore.QSize(22, 22)
        self._row_count = 1
        self._margins = QtCore.QMargins(10, 8, 10, 8)
        self._horizontal_spacing = 6
        self._vertical_spacing = 6
        self._row_height = 38
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Maximum)
        self.setMinimumWidth(0)

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

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(640, self._toolbar_height())

    def minimumSizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(120, self._toolbar_height())

    def _add_item(self, widget: QtWidgets.QWidget) -> None:
        widget.setParent(self)
        widget.show()
        self._items.append(widget)
        QtCore.QTimer.singleShot(0, self._reflow)

    def _reflow(self) -> None:
        if not self._items:
            return

        for widget in self._items:
            widget.hide()

        available_width = max(120, self.width() - self._margins.left() - self._margins.right())
        row = 0
        row_width = 0
        rows: list[list[QtWidgets.QWidget]] = [[], []]

        for leading_separator, widgets in self._toolbar_groups():
            if not widgets:
                continue

            group_widgets = list(widgets)
            include_separator = leading_separator is not None and row_width > 0
            group_items = [leading_separator, *group_widgets] if include_separator else group_widgets
            group_width = self._widgets_width(group_items)
            next_width = (
                group_width
                if row_width == 0
                else row_width + self._horizontal_spacing + group_width
            )

            if row == 0 and row_width > 0 and next_width > available_width:
                row = 1
                row_width = 0
                include_separator = False
                group_items = group_widgets
                group_width = self._widgets_width(group_items)

            rows[row].extend(widget for widget in group_items if widget is not None)
            row_width = group_width if row_width == 0 else row_width + self._horizontal_spacing + group_width

        self._row_count = 2 if rows[1] else 1
        self._position_row_widgets(rows[0], 0)
        self._position_row_widgets(rows[1], 1)
        height = self._toolbar_height()
        if self.minimumHeight() != height:
            self.setMinimumHeight(height)
            self.setMaximumHeight(height)
        self.updateGeometry()

    def _position_row_widgets(self, widgets: list[QtWidgets.QWidget], row: int) -> None:
        x = self._margins.left()
        y = self._margins.top() + row * (self._row_height + self._vertical_spacing)
        for widget in widgets:
            width = self._item_width(widget)
            if widget.objectName() == "ToolbarSeparator":
                separator_height = 22
                widget.setGeometry(
                    x + (width - 1) // 2,
                    y + (self._row_height - separator_height) // 2,
                    1,
                    separator_height,
                )
            else:
                height = min(max(widget.sizeHint().height(), widget.minimumSizeHint().height(), 30), self._row_height)
                widget.setGeometry(x, y + (self._row_height - height) // 2, width, height)
            widget.show()
            x += width + self._horizontal_spacing

    def _toolbar_height(self) -> int:
        height = self._margins.top() + self._margins.bottom() + self._row_count * self._row_height
        if self._row_count > 1:
            height += self._vertical_spacing
        return height

    def _toolbar_groups(self) -> list[tuple[QtWidgets.QWidget | None, list[QtWidgets.QWidget]]]:
        groups: list[tuple[QtWidgets.QWidget | None, list[QtWidgets.QWidget]]] = []
        leading_separator: QtWidgets.QWidget | None = None
        current_group: list[QtWidgets.QWidget] = []

        for widget in self._items:
            if widget.objectName() == "ToolbarSeparator":
                if current_group:
                    groups.append((leading_separator, current_group))
                    current_group = []
                leading_separator = widget
                continue

            current_group.append(widget)

        if current_group:
            groups.append((leading_separator, current_group))

        return groups

    def _widgets_width(self, widgets: list[QtWidgets.QWidget | None]) -> int:
        visible_widgets = [widget for widget in widgets if widget is not None]
        if not visible_widgets:
            return 0

        return sum(self._item_width(widget) for widget in visible_widgets) + self._horizontal_spacing * (
            len(visible_widgets) - 1
        )

    def _item_width(self, widget: QtWidgets.QWidget) -> int:
        if widget.objectName() == "ToolbarSeparator":
            return 11
        if widget.maximumWidth() < 16777215:
            return widget.maximumWidth()
        return max(widget.minimumSizeHint().width(), widget.sizeHint().width(), widget.minimumWidth())
