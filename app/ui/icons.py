from __future__ import annotations

from PySide6 import QtCore, QtGui


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
    elif kind == "question":
        painter.drawEllipse(QtCore.QPointF(12, 12), 7, 7)
        font = QtGui.QFont("DejaVu Sans", 9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QtCore.QRect(8, 5, 8, 11), QtCore.Qt.AlignmentFlag.AlignCenter, "?")
        painter.setBrush(QtGui.QColor(color))
        painter.drawEllipse(QtCore.QPointF(12, 18), 0.8, 0.8)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
    elif kind == "arrow-right":
        painter.drawLine(5, 12, 18, 12)
        painter.drawLine(14, 8, 18, 12)
        painter.drawLine(14, 16, 18, 12)

    painter.end()
    return QtGui.QIcon(pixmap)
