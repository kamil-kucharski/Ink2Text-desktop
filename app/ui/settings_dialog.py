from __future__ import annotations

from PySide6 import QtWidgets

from app.config import AppConfig, SUPPORTED_GEMINI_MODELS
from app.ui.i18n import translate
from app.ui.menu_select import MenuSelectButton
from app.ui.theme import apply_card_shadow


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

        self.resize(460, 220)
        self._build_ui()
        self._populate_fields()
        self._apply_translations()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)

        self.card = QtWidgets.QFrame()
        self.card.setObjectName("SettingsCard")
        card_layout = QtWidgets.QVBoxLayout(self.card)
        card_layout.setContentsMargins(20, 20, 20, 18)
        card_layout.setSpacing(14)

        self.description_label = QtWidgets.QLabel()
        self.description_label.setWordWrap(True)
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

    def _apply_translations(self) -> None:
        self.setWindowTitle(self._tr("settings_title"))
        self.description_label.setText(self._tr("settings_description"))
        self.api_key_label.setText(self._tr("settings_api_key"))
        self.api_key_input.setPlaceholderText(self._tr("settings_api_placeholder"))
        self.model_label.setText(self._tr("settings_model"))
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
