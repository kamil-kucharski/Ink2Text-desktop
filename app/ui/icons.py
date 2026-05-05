from __future__ import annotations

import math

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
        icon_color = QtGui.QColor(color)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(icon_color)

        painter.drawRoundedRect(QtCore.QRectF(7.4, 3.1, 9.2, 6.4), 2.2, 2.2)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Clear)
        painter.drawRoundedRect(QtCore.QRectF(9.5, 5.4, 5.0, 2.6), 1.1, 1.1)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setBrush(icon_color)

        painter.drawRoundedRect(QtCore.QRectF(3.9, 7.5, 16.2, 3.0), 1.4, 1.4)

        body_path = QtGui.QPainterPath()
        body_path.moveTo(5.4, 11.6)
        body_path.lineTo(18.6, 11.6)
        body_path.lineTo(17.6, 20.0)
        body_path.quadTo(17.4, 21.2, 15.8, 21.2)
        body_path.lineTo(8.2, 21.2)
        body_path.quadTo(6.6, 21.2, 6.4, 20.0)
        body_path.closeSubpath()
        painter.drawPath(body_path)

        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Clear)
        for x_position in (8.3, 11.2, 14.1):
            painter.drawRoundedRect(QtCore.QRectF(x_position, 13.0, 1.6, 6.6), 0.8, 0.8)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.setPen(pen)
    elif kind == "sparkle":
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor(color))

        main_star = QtGui.QPainterPath()
        main_star.moveTo(9.0, 3.0)
        main_star.cubicTo(9.7, 7.1, 11.9, 9.3, 16.0, 10.0)
        main_star.cubicTo(11.9, 10.7, 9.7, 12.9, 9.0, 17.0)
        main_star.cubicTo(8.3, 12.9, 6.1, 10.7, 2.0, 10.0)
        main_star.cubicTo(6.1, 9.3, 8.3, 7.1, 9.0, 3.0)
        main_star.closeSubpath()
        painter.drawPath(main_star)

        small_star = QtGui.QPainterPath()
        small_star.moveTo(17.0, 11.5)
        small_star.cubicTo(17.4, 14.0, 18.9, 15.5, 21.4, 16.0)
        small_star.cubicTo(18.9, 16.5, 17.4, 18.0, 17.0, 20.5)
        small_star.cubicTo(16.6, 18.0, 15.1, 16.5, 12.6, 16.0)
        small_star.cubicTo(15.1, 15.5, 16.6, 14.0, 17.0, 11.5)
        small_star.closeSubpath()
        painter.drawPath(small_star)

        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.setPen(pen)
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
        icon_color = QtGui.QColor(color)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(icon_color)

        gear_path = QtGui.QPainterPath()
        for index in range(16):
            angle = -90 + index * 22.5
            angle_radians = math.radians(angle)
            radius = 9.4 if index % 2 == 0 else 6.7
            point = QtCore.QPointF(
                12 + radius * math.cos(angle_radians),
                12 + radius * math.sin(angle_radians),
            )
            if index == 0:
                gear_path.moveTo(point)
            else:
                gear_path.lineTo(point)
        gear_path.closeSubpath()
        painter.drawPath(gear_path)

        for angle in range(0, 360, 45):
            transform = QtGui.QTransform()
            transform.translate(12, 12)
            transform.rotate(angle)
            tooth = QtGui.QPainterPath()
            tooth.addRoundedRect(QtCore.QRectF(-2.05, -10.0, 4.1, 4.2), 0.35, 0.35)
            painter.drawPath(transform.map(tooth))

        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Clear)
        painter.drawEllipse(QtCore.QPointF(12, 12), 3.05, 3.05)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.setPen(pen)
    elif kind == "save":
        icon_color = QtGui.QColor(color)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(icon_color)

        bookmark_path = QtGui.QPainterPath()
        bookmark_path.moveTo(6.0, 3.0)
        bookmark_path.lineTo(18.0, 3.0)
        bookmark_path.quadTo(20.0, 3.0, 20.0, 5.0)
        bookmark_path.lineTo(20.0, 19.0)
        bookmark_path.quadTo(20.0, 21.1, 18.0, 19.9)
        bookmark_path.lineTo(13.1, 16.5)
        bookmark_path.quadTo(12.0, 15.8, 10.9, 16.5)
        bookmark_path.lineTo(6.0, 19.9)
        bookmark_path.quadTo(4.0, 21.1, 4.0, 19.0)
        bookmark_path.lineTo(4.0, 5.0)
        bookmark_path.quadTo(4.0, 3.0, 6.0, 3.0)
        bookmark_path.closeSubpath()
        painter.drawPath(bookmark_path)

        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.setPen(pen)
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
        painter.drawEllipse(QtCore.QPointF(12, 12), 8, 8)
        font = QtGui.QFont("DejaVu Sans", 10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QtCore.QRectF(7.2, 5.2, 9.6, 14.0), QtCore.Qt.AlignmentFlag.AlignCenter, "?")
    elif kind == "arrow-right":
        painter.drawLine(5, 12, 18, 12)
        painter.drawLine(14, 8, 18, 12)
        painter.drawLine(14, 16, 18, 12)

    painter.end()
    return QtGui.QIcon(pixmap)
