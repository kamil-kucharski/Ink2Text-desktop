from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from app.config import AppConfig, SUPPORTED_GEMINI_MODELS
from app.ui.i18n import translate
from app.ui.menu_select import MenuSelectButton
from app.ui.settings_dialog import LanguageSwitch


class OnboardingDialog(QtWidgets.QDialog):
    def __init__(
        self,
        app_config: AppConfig,
        language: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_config = app_config
        self.language = language if language in {"pl", "en"} else "pl"
        self.resize(640, 610)
        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)

        self._build_ui()
        self._populate_fields()
        self._apply_translations()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        self.card = QtWidgets.QFrame()
        self.card.setObjectName("SettingsCard")
        card_layout = QtWidgets.QVBoxLayout(self.card)
        card_layout.setContentsMargins(26, 26, 26, 22)
        card_layout.setSpacing(18)

        self.title_label = QtWidgets.QLabel()
        self.title_label.setObjectName("DialogTitle")
        self.subtitle_label = QtWidgets.QLabel()
        self.subtitle_label.setObjectName("DialogSubtitle")
        self.subtitle_label.setWordWrap(True)
        card_layout.addWidget(self.title_label)
        card_layout.addWidget(self.subtitle_label)

        self.language_section_label = QtWidgets.QLabel()
        self.language_section_label.setObjectName("SettingsSectionTitle")
        self.language_switch = LanguageSwitch()
        self.language_switch.languageChanged.connect(self._change_language)
        card_layout.addWidget(self.language_section_label)
        card_layout.addWidget(self.language_switch)

        self.ai_section_label = QtWidgets.QLabel()
        self.ai_section_label.setObjectName("SettingsSectionTitle")
        self.ai_description_label = QtWidgets.QLabel()
        self.ai_description_label.setObjectName("DialogSubtitle")
        self.ai_description_label.setWordWrap(True)
        card_layout.addWidget(self.ai_section_label)
        card_layout.addWidget(self.ai_description_label)

        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        self.api_key_label = QtWidgets.QLabel()
        self.api_key_input = QtWidgets.QLineEdit()
        self.api_key_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        form.addRow(self.api_key_label, self.api_key_input)

        self.model_label = QtWidgets.QLabel()
        self.model_input = MenuSelectButton()
        self.model_input.setObjectName("SettingsModelButton")
        self.model_input.addItems(list(SUPPORTED_GEMINI_MODELS))
        form.addRow(self.model_label, self.model_input)
        card_layout.addLayout(form)

        self.steps_label = QtWidgets.QLabel()
        self.steps_label.setObjectName("DialogSubtitle")
        self.steps_label.setWordWrap(True)
        card_layout.addWidget(self.steps_label)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        self.start_button = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.cancel_button = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        card_layout.addWidget(buttons)

        layout.addWidget(self.card)

    def _populate_fields(self) -> None:
        self.language_switch.set_language(self.language)
        self.api_key_input.setText(self.app_config.gemini_api_key or "")
        index = self.model_input.findText(self.app_config.gemini_model)
        self.model_input.setCurrentIndex(index if index >= 0 else 0)

    def _change_language(self, language: str) -> None:
        self.language = language if language in {"pl", "en"} else "pl"
        self._apply_translations()

    def _apply_translations(self) -> None:
        self.setWindowTitle(self._tr("onboarding_title"))
        self.title_label.setText(self._tr("onboarding_title"))
        self.subtitle_label.setText(self._tr("onboarding_subtitle"))
        self.language_section_label.setText(self._tr("settings_language_section"))
        self.language_switch.set_labels(
            self._tr("settings_lang_polish"),
            self._tr("settings_lang_english"),
        )
        self.ai_section_label.setText(self._tr("settings_ai_section"))
        self.ai_description_label.setText(self._tr("onboarding_ai_description"))
        self.api_key_label.setText(self._tr("settings_api_key"))
        self.api_key_input.setPlaceholderText(self._tr("settings_api_placeholder"))
        self.model_label.setText(self._tr("settings_model"))
        self.model_input.setPlaceholderText(self._tr("select_placeholder"))
        self.steps_label.setText(self._tr("onboarding_steps"))
        self.start_button.setText(self._tr("onboarding_start"))
        self.cancel_button.setText(self._tr("onboarding_later"))

    @property
    def api_key(self) -> str:
        return self.api_key_input.text().strip()

    @property
    def model_name(self) -> str:
        return self.model_input.currentText()

    @property
    def app_language(self) -> str:
        return self.language

    def _tr(self, key: str, **kwargs) -> str:
        return translate(self.language, key, **kwargs)
