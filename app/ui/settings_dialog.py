from __future__ import annotations

from PySide6 import QtWidgets

from app.config import AppConfig, SUPPORTED_GEMINI_MODELS


class AISettingsDialog(QtWidgets.QDialog):
    def __init__(self, app_config: AppConfig, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.app_config = app_config

        self.setWindowTitle("Ustawienia AI")
        self.resize(460, 220)
        self._build_ui()
        self._populate_fields()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        description = QtWidgets.QLabel(
            "Ustaw lokalny klucz Gemini i wybierz model, którego aplikacja ma używać."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        form = QtWidgets.QFormLayout()
        self.api_key_input = QtWidgets.QLineEdit()
        self.api_key_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Wklej klucz API Gemini")
        form.addRow("Klucz API", self.api_key_input)

        self.model_input = QtWidgets.QComboBox()
        self.model_input.addItems(list(SUPPORTED_GEMINI_MODELS))
        form.addRow("Model", self.model_input)
        layout.addLayout(form)

        self.info_label = QtWidgets.QLabel(
            f"Ustawienia zostaną zapisane lokalnie w: {self.app_config.config_path}"
        )
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #666;")
        layout.addWidget(self.info_label)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Save
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
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
            QtWidgets.QMessageBox.warning(self, "Brak klucza", "Wpisz klucz API Gemini.")
            return

        self.accept()

    @property
    def api_key(self) -> str:
        return self.api_key_input.text().strip()

    @property
    def model_name(self) -> str:
        return self.model_input.currentText().strip()
