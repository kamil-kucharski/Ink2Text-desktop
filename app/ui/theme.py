from __future__ import annotations

from PySide6 import QtGui, QtWidgets


APP_STYLE_SHEET = """
QMainWindow {
    background: #eef1f5;
}
QWidget#AppRoot {
    background: transparent;
}
QFrame#HeaderBar,
QFrame#WorkspaceShell,
QFrame#SettingsCard {
    background: rgba(250, 251, 253, 0.98);
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 20px;
}
QFrame#SidebarPane,
QFrame#ContentPane,
QFrame#MetaSection,
QFrame#ImagesSection,
QFrame#EditorSection {
    background: transparent;
    border: none;
}
QLabel#HeaderEyebrow {
    color: #64748b;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
QLabel#HeroTitle {
    color: #111827;
    font-size: 30px;
    font-weight: 700;
}
QLabel#HeroSubtitle {
    color: #6b7280;
    font-size: 13px;
    line-height: 1.45;
}
QLabel#SectionLabel {
    color: #6b7280;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.04em;
}
QLabel#CountBadge,
QLabel#StatusPill {
    background: rgba(255, 255, 255, 0.92);
    color: #475569;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#ModeInlineLabel {
    color: #6b7280;
    font-size: 12px;
    font-weight: 600;
}
QPushButton,
QToolButton,
QPushButton::menu-indicator,
QLineEdit,
QTextEdit,
QListWidget,
QLabel {
    color: #0f172a;
}
QPushButton {
    min-height: 36px;
    padding: 0 14px;
    border-radius: 12px;
    border: 1px solid rgba(15, 23, 42, 0.10);
    background: rgba(255, 255, 255, 0.90);
    font-weight: 600;
}
QPushButton:hover {
    background: rgba(255, 255, 255, 1);
    border-color: rgba(15, 23, 42, 0.14);
}
QPushButton:pressed {
    background: rgba(243, 244, 246, 1);
}
QPushButton[variant="primary"] {
    background: #111827;
    color: white;
    border: none;
    padding: 0 18px;
}
QPushButton[variant="primary"]:hover {
    background: #0f172a;
}
QPushButton[variant="danger"] {
    background: rgba(255, 255, 255, 0.88);
    color: #b42318;
    border: 1px solid rgba(217, 45, 32, 0.16);
}
QPushButton[variant="subtle"] {
    background: rgba(247, 248, 250, 0.98);
}
QPushButton#LanguageButton,
QPushButton#ModeButton,
QPushButton#FontFamilyButton,
QPushButton#FontSizeButton,
QPushButton#SettingsModelButton {
    text-align: left;
    padding-left: 12px;
    padding-right: 12px;
}
QLineEdit,
QTextEdit {
    background: rgba(255, 255, 255, 0.98);
    border: 1px solid rgba(15, 23, 42, 0.10);
    border-radius: 14px;
    padding: 10px 12px;
    selection-background-color: rgba(17, 24, 39, 0.16);
}
QLineEdit:focus,
QTextEdit:focus,
QListWidget:focus {
    border: 1px solid rgba(17, 24, 39, 0.18);
}
QLineEdit#TitleInput {
    min-height: 46px;
    font-size: 24px;
    font-weight: 700;
    padding: 10px 2px 12px 2px;
    border: none;
    border-bottom: 1px solid rgba(15, 23, 42, 0.10);
    border-radius: 0;
    background: transparent;
}
QToolBar#EditorToolbar {
    background: rgba(246, 247, 249, 1);
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 14px;
    spacing: 8px;
    padding: 8px;
}
QToolBar#EditorToolbar QToolButton {
    min-width: 34px;
    min-height: 34px;
    border-radius: 10px;
    border: 1px solid transparent;
    background: transparent;
}
QToolBar#EditorToolbar QToolButton:hover {
    background: rgba(229, 231, 235, 0.95);
}
QToolBar#EditorToolbar QToolButton:checked {
    background: rgba(17, 24, 39, 0.10);
    border-color: rgba(17, 24, 39, 0.12);
}
QListWidget#NoteList,
QListWidget#ImageList {
    background: transparent;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 14px;
    padding: 8px;
    outline: none;
}
QListWidget#NoteList::item,
QListWidget#ImageList::item {
    border-radius: 12px;
    padding: 10px 12px;
    margin: 3px 0;
}
QListWidget#NoteList::item:hover,
QListWidget#ImageList::item:hover {
    background: rgba(243, 244, 246, 0.96);
}
QListWidget#NoteList::item:selected,
QListWidget#ImageList::item:selected {
    background: rgba(17, 24, 39, 0.08);
    border: 1px solid rgba(17, 24, 39, 0.08);
    color: #0f172a;
}
QLabel#ImagePreview {
    background: rgba(245, 247, 250, 1);
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 16px;
    color: #64748b;
}
QSplitter::handle {
    background: transparent;
    width: 10px;
    height: 10px;
}
QStatusBar {
    background: rgba(250, 251, 253, 0.88);
    border-top: 1px solid rgba(15, 23, 42, 0.08);
    color: #6b7280;
}
QMenu {
    background: rgba(255, 255, 255, 0.98);
    border: 1px solid rgba(15, 23, 42, 0.10);
    border-radius: 12px;
    padding: 8px;
}
QMenu::item {
    padding: 8px 12px;
    border-radius: 8px;
}
QMenu::item:selected {
    background: rgba(17, 24, 39, 0.08);
}
QScrollBar:vertical,
QScrollBar:horizontal {
    background: transparent;
    border: none;
    margin: 0;
}
QScrollBar:vertical {
    width: 10px;
}
QScrollBar:horizontal {
    height: 10px;
}
QScrollBar::handle {
    background: rgba(148, 163, 184, 0.56);
    border-radius: 999px;
}
QScrollBar::handle:hover {
    background: rgba(100, 116, 139, 0.72);
}
QScrollBar::add-line,
QScrollBar::sub-line,
QScrollBar::add-page,
QScrollBar::sub-page {
    background: transparent;
    border: none;
}
QDialog {
    background: #eef1f5;
}
"""


def apply_theme(application: QtWidgets.QApplication) -> None:
    application.setStyle("Fusion")
    application.setStyleSheet(APP_STYLE_SHEET)
    application.setFont(_pick_font())


def apply_card_shadow(widget: QtWidgets.QWidget, blur_radius: float = 24.0) -> None:
    shadow = QtWidgets.QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur_radius)
    shadow.setOffset(0, 6)
    shadow.setColor(QtGui.QColor(15, 23, 42, 18))
    widget.setGraphicsEffect(shadow)


def _pick_font() -> QtGui.QFont:
    preferred_families = (
        "SF Pro Text",
        "Aptos",
        "Segoe UI",
        "Noto Sans",
        "Inter",
        "DejaVu Sans",
    )
    available = set(QtGui.QFontDatabase.families())
    for family in preferred_families:
        if family in available:
            font = QtGui.QFont(family, 10)
            font.setHintingPreference(QtGui.QFont.HintingPreference.PreferFullHinting)
            return font

    font = QtGui.QFont()
    font.setPointSize(10)
    return font
