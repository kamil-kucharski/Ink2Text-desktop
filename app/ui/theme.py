from __future__ import annotations

from PySide6 import QtGui, QtWidgets


APP_STYLE_SHEET = """
QMainWindow {
    background: #f5f7fb;
}
QWidget#AppRoot,
QWidget#MainArea {
    background: #f5f7fb;
}
QFrame#SidebarPane {
    background: #fbfcff;
    border-right: 1px solid #e6ebf3;
}
QLabel#LogoMark {
    min-width: 38px;
    min-height: 38px;
    max-width: 38px;
    max-height: 38px;
    background: transparent;
}
QLabel#LogoLabel {
    color: #101a33;
    font-size: 17px;
    font-weight: 800;
}
QFrame#NoteItemWidget {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 13px;
}
QFrame#NoteItemWidget:hover {
    background: #f1f5fb;
}
QFrame#NoteItemWidget[active="true"] {
    background: #eef3ff;
    border-left: 3px solid #1e3a8a;
}
QLabel#NoteItemTitle,
QLabel#TrashNoteTitle {
    color: #24324b;
    font-size: 13px;
    font-weight: 700;
}
QLabel#NoteItemMeta,
QLabel#TrashNoteMeta {
    color: #7b879d;
    font-size: 12px;
}
QLabel#SidebarSectionLabel,
QLabel#ControlLabel,
QLabel#AssistantSectionLabel {
    color: #66728a;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.06em;
}
QLabel#SidebarCountLabel,
QLabel#HelperText,
QLabel#MetaText,
QLabel#StatusMeta {
    color: #7b879d;
    font-size: 12px;
}
QFrame#ContentCard,
QFrame#PhotosPanel,
QFrame#EditorPanel,
QFrame#AssistantPanel {
    background: #ffffff;
    border: 1px solid #e4e9f2;
    border-radius: 0;
}
QFrame#PhotosPanel {
    border-bottom: none;
}
QFrame#AssistantPanel {
    border-left: none;
}
QFrame#TopBar {
    background: transparent;
    border: none;
}
QFrame#TopSeparator,
QFrame#AssistantSeparator {
    color: #e4e9f2;
    background: #e4e9f2;
}
QLabel#CardTitle,
QLabel#AssistantTitle {
    color: #101a33;
    font-size: 18px;
    font-weight: 800;
}
QLabel#AssistantDescription,
QLabel#InfoLabel,
QLabel#TipText {
    color: #7b879d;
    font-size: 13px;
    line-height: 1.45;
}
QLabel#InfoValue {
    color: #5c6880;
    font-size: 12px;
    font-weight: 700;
}
QLabel#TipTitle {
    color: #1e3a8a;
    font-size: 13px;
    font-weight: 800;
}
QLabel#TipText {
    color: #66728a;
    font-size: 13px;
    line-height: 1.45;
}
QLabel#TitleIconTile,
QPushButton#TitleIconButton {
    min-width: 44px;
    min-height: 44px;
    max-width: 44px;
    max-height: 44px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid #e4e9f2;
    padding: 0;
}
QPushButton#TitleIconButton:hover {
    background: #ffffff;
    border-color: #d5deeb;
}
QPushButton#TitleIconButton:pressed {
    background: #f1f5fb;
}
QLabel#DialogTitle {
    color: #101a33;
    font-size: 22px;
    font-weight: 800;
}
QLabel#DialogSubtitle,
QLabel#TrashEmpty {
    color: #6d7890;
    font-size: 13px;
}
QLabel#TrashEmpty {
    background: #fbfcff;
    border: 1px dashed #cdd6e6;
    border-radius: 16px;
    padding: 28px;
}
QFrame#TipCard {
    background: #f3f6ff;
    border: 1px solid #dbe5ff;
    border-radius: 10px;
}
QFrame#SettingsCard {
    background: #ffffff;
    border: 1px solid #e4e9f2;
    border-radius: 18px;
}
QFrame#SettingsSeparator {
    color: #e4e9f2;
    background: #e4e9f2;
}
QLabel#SettingsSectionTitle {
    color: #172b65;
    font-size: 14px;
    font-weight: 800;
}
QFrame#LanguageSwitch {
    background: #f1f5fb;
    border: 1px solid #dfe5ef;
    border-radius: 16px;
}
QWidget#LoadingOverlay {
    background: rgba(245, 247, 251, 176);
}
QFrame#LoadingCard {
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid #e4e9f2;
    border-radius: 22px;
}
QLabel#LoadingLabel {
    color: #172b65;
    font-size: 17px;
    font-weight: 800;
}
QPushButton,
QToolButton,
QLineEdit,
QTextEdit,
QListWidget,
QLabel {
    color: #111827;
}
QPushButton {
    min-height: 34px;
    padding: 0 15px;
    border-radius: 11px;
    border: 1px solid #dfe5ef;
    background: #ffffff;
    font-size: 13px;
    font-weight: 700;
}
QPushButton:hover {
    background: #f8faff;
    border-color: #cfd8e8;
}
QPushButton:pressed {
    background: #eef3ff;
}
QPushButton[variant="primary"],
QPushButton#SidebarPrimaryButton,
QPushButton#AssistantPrimaryButton {
    background: #172b65;
    color: #ffffff;
    border: 1px solid #172b65;
}
QPushButton[variant="primary"]:hover,
QPushButton#SidebarPrimaryButton:hover,
QPushButton#AssistantPrimaryButton:hover {
    background: #1e3a8a;
    border-color: #1e3a8a;
}
QPushButton#AssistantPrimaryButton {
    min-height: 46px;
    border-radius: 14px;
    font-size: 14px;
    margin-top: 8px;
}
QPushButton[variant="danger"] {
    color: #b42318;
    background: #fffafa;
    border-color: #f2d4d1;
}
QPushButton[variant="link"],
QPushButton#SidebarLinkButton {
    text-align: left;
    background: transparent;
    border: 1px solid transparent;
    color: #66728a;
    padding-left: 4px;
    padding-right: 6px;
    min-height: 40px;
    font-size: 14px;
    font-weight: 700;
}
QPushButton[variant="link"]:hover,
QPushButton#SidebarLinkButton:hover {
    background: transparent;
    color: #4f5f78;
}
QPushButton#IconButton {
    min-width: 34px;
    max-width: 34px;
    min-height: 34px;
    max-height: 34px;
    padding: 0;
    border-radius: 10px;
    color: #66728a;
}
QPushButton#TopActionButton {
    min-width: 176px;
    max-width: 176px;
    min-height: 32px;
    max-height: 32px;
    padding: 0 16px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid #e4e9f2;
    color: #172b65;
    font-size: 12px;
    font-weight: 800;
}
QPushButton#TopActionButton:hover {
    background: #ffffff;
    border-color: #d5deeb;
}
QPushButton#TopActionButton:pressed {
    background: #f1f5fb;
}
QPushButton#AddImageButton {
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
    border-radius: 10px;
    background: #f1f5fb;
    border: 1px solid #dfe5ef;
    color: #172b65;
    font-size: 18px;
    font-weight: 800;
}
QPushButton#AddImageButton:hover {
    background: #eaf0fb;
    border-color: #cfd8e8;
}
QPushButton#InlineTrashButton {
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    padding: 0;
    border-radius: 10px;
    background: transparent;
    border-color: transparent;
    color: #c4322b;
}
QPushButton#InlineTrashButton:hover {
    background: transparent;
    border-color: transparent;
    color: #b42318;
}
QPushButton#ThumbnailTrashButton {
    min-width: 34px;
    max-width: 34px;
    min-height: 34px;
    max-height: 34px;
    padding: 0;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.86);
    border: 1px solid rgba(226, 232, 240, 0.90);
    color: #c4322b;
}
QPushButton#ThumbnailTrashButton:hover {
    background: rgba(255, 255, 255, 0.96);
    border-color: #f2d4d1;
}
QPushButton#TrashRestoreButton {
    min-height: 32px;
    color: #1e3a8a;
    background: #eef3ff;
    border-color: #d5e0ff;
}
QPushButton#TrashDeleteButton {
    min-height: 32px;
    color: #b42318;
    background: #fffafa;
    border-color: #f2d4d1;
}
QPushButton#DialogCloseButton {
    min-width: 96px;
}
QPushButton#LanguageSwitchButton {
    min-height: 46px;
    border-radius: 12px;
    border: 1px solid transparent;
    background: transparent;
    color: #66728a;
    font-weight: 800;
    text-align: left;
    padding: 0 14px;
}
QPushButton#LanguageSwitchButton:hover {
    background: rgba(255, 255, 255, 0.72);
}
QPushButton#LanguageSwitchButton[active="true"] {
    background: #ffffff;
    border-color: #d8e0ed;
    color: #172b65;
}
QPushButton#LanguageButton,
QPushButton#ModeButton,
QPushButton#AssistantModeButton,
QPushButton#FontFamilyButton,
QPushButton#FontSizeButton,
QPushButton#SettingsModelButton {
    text-align: left;
    min-height: 38px;
    border-radius: 10px;
    background: #ffffff;
    border: 1px solid #dfe5ef;
    color: #2b354a;
    font-size: 13px;
    font-weight: 700;
    padding-left: 18px;
    padding-right: 34px;
}
QPushButton[selectMenu="true"]::menu-indicator {
    image: none;
    width: 0;
}
QPushButton#LanguageButton:hover,
QPushButton#ModeButton:hover,
QPushButton#AssistantModeButton:hover,
QPushButton#FontFamilyButton:hover,
QPushButton#FontSizeButton:hover,
QPushButton#SettingsModelButton:hover {
    background: #fbfcff;
    border-color: #cfd8e8;
}
QPushButton#LanguageButton:pressed,
QPushButton#ModeButton:pressed,
QPushButton#AssistantModeButton:pressed,
QPushButton#FontFamilyButton:pressed,
QPushButton#FontSizeButton:pressed,
QPushButton#SettingsModelButton:pressed {
    background: #f1f5fb;
}
QPushButton#AssistantModeButton {
    min-height: 52px;
    border-radius: 12px;
    font-size: 14px;
    padding-left: 20px;
    padding-right: 38px;
}
QLineEdit,
QTextEdit {
    background: #ffffff;
    border: 1px solid #dfe5ef;
    border-radius: 12px;
    padding: 10px 12px;
    selection-background-color: rgba(30, 58, 138, 0.18);
}
QLineEdit:focus,
QTextEdit:focus,
QListWidget:focus {
    border: 1px solid #b9c7df;
}
QLineEdit#SearchInput {
    min-height: 34px;
    background: #ffffff;
    color: #334155;
}
QLineEdit#TitleInput {
    min-height: 30px;
    padding: 0;
    border: none;
    border-radius: 0;
    background: transparent;
    color: #101a33;
    font-size: 24px;
    font-weight: 800;
}
QLabel#ImageCounter {
    color: #7b879d;
    font-size: 13px;
    font-weight: 700;
    padding: 0 6px;
}
QLabel#ThumbnailEmpty {
    min-height: 52px;
    background: #fbfcff;
    border: 1px dashed #cdd6e6;
    border-radius: 16px;
    color: #7b879d;
    font-size: 13px;
    padding: 16px;
}
QFrame#ImageThumbnailWidget {
    background: #ffffff;
    border: 1px solid #e1e7f0;
    border-radius: 11px;
}
QFrame#ImageThumbnailWidget[active="true"] {
    border: 2px solid #1e3a8a;
}
QFrame#ImageThumbnailWidget:hover {
    border-color: #b9c7df;
    background: #fbfcff;
}
QLabel#ThumbnailImage {
    background: #f1f5fb;
    border: 1px solid transparent;
    border-radius: 10px;
}
QLabel#PreviewImage {
    background: #fbfcff;
    border: 1px solid #e4e9f2;
    border-radius: 18px;
    color: #6d7890;
}
QTextEdit#ContentEditor {
    min-height: 260px;
    border-radius: 0;
    border-top: none;
    color: #172033;
    font-size: 14px;
}
QFrame#EditorToolbar {
    background: #f8fafd;
    border: 1px solid #dfe5ef;
    border-radius: 0;
}
QFrame#EditorToolbar QToolButton {
    min-width: 34px;
    min-height: 34px;
    border-radius: 10px;
    border: 1px solid transparent;
    background: transparent;
    color: #172b65;
}
QFrame#EditorToolbar QToolButton:hover {
    background: #eef3ff;
    border-color: #dbe5ff;
}
QFrame#EditorToolbar QToolButton:checked {
    background: #e4ecff;
    border-color: #cbd8ff;
}
QFrame#EditorToolbar QFrame#ToolbarSeparator {
    min-width: 1px;
    max-width: 1px;
    background: #e2e8f2;
    margin: 7px 5px;
}
QListWidget#NoteList {
    background: transparent;
    border: none;
    outline: none;
}
QListWidget#NoteList::item,
QListWidget#TrashList::item {
    border-radius: 13px;
    padding: 0;
    color: #34415a;
}
QListWidget#TrashList {
    background: transparent;
    border: none;
    outline: none;
}
QFrame#TrashNoteWidget {
    background: #ffffff;
    border: 1px solid #e4e9f2;
    border-radius: 14px;
}
QFrame#TrashNoteWidget:hover {
    background: #fbfcff;
    border-color: #d5deeb;
}
QLabel#InfoIcon,
QLabel#AssistantIcon,
QLabel#TipIcon {
    min-width: 22px;
    max-width: 22px;
}
QListWidget#ImageList {
    background: transparent;
    border: none;
    outline: none;
}
QListWidget#ImageList::item {
    border-radius: 13px;
    padding: 4px;
    margin: 0 2px;
}
QListWidget#ImageList::item:hover {
    background: #f1f5fb;
}
QListWidget#ImageList::item:selected {
    background: transparent;
    border: none;
}
QStatusBar {
    background: #fbfcff;
    border-top: 1px solid #e6ebf3;
    color: #7b879d;
    min-height: 26px;
}
QMenu,
QMenu#SelectMenu {
    background: #ffffff;
    border: 1px solid #d8e0ed;
    border-radius: 14px;
    padding: 7px;
    color: #263148;
}
QMenu::item,
QMenu#SelectMenu::item {
    min-height: 28px;
    padding: 8px 32px 8px 18px;
    border-radius: 9px;
    background: transparent;
}
QMenu::item:selected,
QMenu#SelectMenu::item:selected {
    background: #eef3ff;
    color: #172b65;
}
QMenu::separator,
QMenu#SelectMenu::separator {
    height: 1px;
    background: #edf1f7;
    margin: 6px 8px;
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
    background: rgba(148, 163, 184, 0.55);
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
    background: #f5f7fb;
}
"""


def apply_theme(application: QtWidgets.QApplication) -> None:
    application.setStyle("Fusion")
    application.setStyleSheet(APP_STYLE_SHEET)
    application.setFont(_pick_font())


def apply_card_shadow(widget: QtWidgets.QWidget, blur_radius: float = 24.0) -> None:
    shadow = QtWidgets.QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur_radius)
    shadow.setOffset(0, 5)
    shadow.setColor(QtGui.QColor(15, 23, 42, 16))
    widget.setGraphicsEffect(shadow)


def _pick_font() -> QtGui.QFont:
    preferred_families = (
        "SF Pro Text",
        "Inter",
        "Segoe UI",
        "Aptos",
        "Noto Sans",
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
