from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from app.config import AppConfig, SUPPORTED_GEMINI_MODELS
from app.ui.i18n import translate
from app.ui.menu_select import MenuSelectButton
from app.ui.theme import apply_card_shadow


def _flag_icon(language: str) -> QtGui.QIcon:
    pixmap = QtGui.QPixmap(34, 24)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    rect = QtCore.QRectF(1, 1, 32, 22)
    path = QtGui.QPainterPath()
    path.addRoundedRect(rect, 5, 5)
    painter.setClipPath(path)

    if language == "pl":
        painter.fillRect(rect, QtGui.QColor("#ffffff"))
        painter.fillRect(QtCore.QRectF(1, 12, 32, 11), QtGui.QColor("#dc143c"))
    else:
        painter.fillRect(rect, QtGui.QColor("#1f3f8b"))
        white_pen = QtGui.QPen(QtGui.QColor("#ffffff"), 5)
        red_pen = QtGui.QPen(QtGui.QColor("#c8102e"), 2.6)
        painter.setPen(white_pen)
        painter.drawLine(1, 1, 33, 23)
        painter.drawLine(33, 1, 1, 23)
        painter.setPen(red_pen)
        painter.drawLine(1, 1, 33, 23)
        painter.drawLine(33, 1, 1, 23)
        painter.fillRect(QtCore.QRectF(1, 9, 32, 6), QtGui.QColor("#ffffff"))
        painter.fillRect(QtCore.QRectF(14, 1, 6, 22), QtGui.QColor("#ffffff"))
        painter.fillRect(QtCore.QRectF(1, 10.5, 32, 3), QtGui.QColor("#c8102e"))
        painter.fillRect(QtCore.QRectF(15.5, 1, 3, 22), QtGui.QColor("#c8102e"))

    painter.setClipping(False)
    painter.setPen(QtGui.QPen(QtGui.QColor("#d5dce8"), 1))
    painter.drawRoundedRect(rect, 5, 5)
    painter.end()
    return QtGui.QIcon(pixmap)


class LanguageSwitch(QtWidgets.QFrame):
    languageChanged = QtCore.Signal(str)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("LanguageSwitch")
        self._language = "pl"

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.polish_button = QtWidgets.QPushButton()
        self.polish_button.setObjectName("LanguageSwitchButton")
        self.polish_button.setIcon(_flag_icon("pl"))
        self.polish_button.setIconSize(QtCore.QSize(34, 24))
        self.polish_button.clicked.connect(lambda: self.set_language("pl"))

        self.english_button = QtWidgets.QPushButton()
        self.english_button.setObjectName("LanguageSwitchButton")
        self.english_button.setIcon(_flag_icon("en"))
        self.english_button.setIconSize(QtCore.QSize(34, 24))
        self.english_button.clicked.connect(lambda: self.set_language("en"))

        layout.addWidget(self.polish_button)
        layout.addWidget(self.english_button)

    @property
    def language(self) -> str:
        return self._language

    def set_labels(self, polish: str, english: str) -> None:
        self.polish_button.setText(polish)
        self.english_button.setText(english)

    def set_language(self, language: str) -> None:
        if language not in {"pl", "en"}:
            language = "pl"

        changed = language != self._language
        self._language = language
        self._sync_state()
        if changed:
            self.languageChanged.emit(language)

    def _sync_state(self) -> None:
        for button, language in (
            (self.polish_button, "pl"),
            (self.english_button, "en"),
        ):
            button.setProperty("active", language == self._language)
            button.style().unpolish(button)
            button.style().polish(button)


class AISettingsDialog(QtWidgets.QDialog):
    def __init__(
        self,
        app_config: AppConfig,
        language: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_config = app_config
        self.language = language

        self.resize(540, 430)
        self._build_ui()
        self._populate_fields()
        self._apply_translations()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)

        self.card = QtWidgets.QFrame()
        self.card.setObjectName("SettingsCard")
        card_layout = QtWidgets.QVBoxLayout(self.card)
        card_layout.setContentsMargins(22, 22, 22, 20)
        card_layout.setSpacing(18)

        self.title_label = QtWidgets.QLabel()
        self.title_label.setObjectName("DialogTitle")
        card_layout.addWidget(self.title_label)

        self.ai_section_label = QtWidgets.QLabel()
        self.ai_section_label.setObjectName("SettingsSectionTitle")
        self.description_label = QtWidgets.QLabel()
        self.description_label.setObjectName("DialogSubtitle")
        self.description_label.setWordWrap(True)
        card_layout.addWidget(self.ai_section_label)
        card_layout.addWidget(self.description_label)

        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        self.api_key_input = QtWidgets.QLineEdit()
        self.api_key_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.api_key_label = QtWidgets.QLabel()
        form.addRow(self.api_key_label, self.api_key_input)

        self.model_input = MenuSelectButton()
        self.model_input.setObjectName("SettingsModelButton")
        self.model_input.addItems(list(SUPPORTED_GEMINI_MODELS))
        self.model_label = QtWidgets.QLabel()
        form.addRow(self.model_label, self.model_input)
        card_layout.addLayout(form)

        separator = QtWidgets.QFrame()
        separator.setObjectName("SettingsSeparator")
        separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        card_layout.addWidget(separator)

        self.language_section_label = QtWidgets.QLabel()
        self.language_section_label.setObjectName("SettingsSectionTitle")
        self.language_description_label = QtWidgets.QLabel()
        self.language_description_label.setObjectName("DialogSubtitle")
        self.language_description_label.setWordWrap(True)
        self.language_switch = LanguageSwitch()
        card_layout.addWidget(self.language_section_label)
        card_layout.addWidget(self.language_description_label)
        card_layout.addWidget(self.language_switch)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.save_button = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Save)
        self.cancel_button = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        card_layout.addWidget(buttons)
        layout.addWidget(self.card)
        apply_card_shadow(self.card, blur_radius=30.0)

    def _populate_fields(self) -> None:
        self.api_key_input.setText(self.app_config.gemini_api_key or "")
        self.language_switch.set_language(self.language)

        index = self.model_input.findText(self.app_config.gemini_model)
        if index >= 0:
            self.model_input.setCurrentIndex(index)

    def _validate_and_accept(self) -> None:
        if not self.api_key.strip():
            QtWidgets.QMessageBox.warning(
                self,
                self._tr("settings_missing_key_title"),
                self._tr("settings_missing_key_message"),
            )
            return

        self.accept()

    @property
    def api_key(self) -> str:
        return self.api_key_input.text().strip()

    @property
    def model_name(self) -> str:
        return self.model_input.currentText().strip()

    @property
    def app_language(self) -> str:
        return self.language_switch.language

    def _apply_translations(self) -> None:
        self.setWindowTitle(self._tr("settings_title"))
        self.title_label.setText(self._tr("settings_title"))
        self.ai_section_label.setText(self._tr("settings_ai_section"))
        self.description_label.setText(self._tr("settings_description"))
        self.api_key_label.setText(self._tr("settings_api_key"))
        self.api_key_input.setPlaceholderText(self._tr("settings_api_placeholder"))
        self.model_label.setText(self._tr("settings_model"))
        self.model_input.setPlaceholderText(self._tr("select_placeholder"))
        self.language_section_label.setText(self._tr("settings_language_section"))
        self.language_description_label.setText(self._tr("settings_language_description"))
        self.language_switch.set_labels(
            self._tr("settings_lang_polish"),
            self._tr("settings_lang_english"),
        )
        self.api_key_label.setObjectName("SectionLabel")
        self.model_label.setObjectName("SectionLabel")
        if self.save_button is not None:
            self.save_button.setText(self._tr("settings_save"))
            self.save_button.setProperty("variant", "primary")
            self.save_button.style().unpolish(self.save_button)
            self.save_button.style().polish(self.save_button)
        if self.cancel_button is not None:
            self.cancel_button.setText(self._tr("settings_cancel"))
            self.cancel_button.setProperty("variant", "subtle")
            self.cancel_button.style().unpolish(self.cancel_button)
            self.cancel_button.style().polish(self.cancel_button)

    def _tr(self, key: str, **kwargs) -> str:
        return translate(self.language, key, **kwargs)
