from __future__ import annotations

from PySide6 import QtWidgets

from app.config import AppConfig, SUPPORTED_GEMINI_MODELS
from app.ui.i18n import translate
from app.ui.menu_select import MenuSelectButton


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

        self.description_label = QtWidgets.QLabel()
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)

        form = QtWidgets.QFormLayout()
        self.api_key_input = QtWidgets.QLineEdit()
        self.api_key_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.api_key_label = QtWidgets.QLabel()
        form.addRow(self.api_key_label, self.api_key_input)

        self.model_input = MenuSelectButton()
        self.model_input.addItems(list(SUPPORTED_GEMINI_MODELS))
        self.model_label = QtWidgets.QLabel()
        form.addRow(self.model_label, self.model_input)
        layout.addLayout(form)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.save_button = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Save)
        self.cancel_button = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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
        if self.save_button is not None:
            self.save_button.setText(self._tr("settings_save"))
        if self.cancel_button is not None:
            self.cancel_button.setText(self._tr("settings_cancel"))

    def _tr(self, key: str, **kwargs) -> str:
        return translate(self.language, key, **kwargs)
