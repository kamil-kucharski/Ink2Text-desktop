from __future__ import annotations

import sys
import os
from pathlib import Path


def _prefer_stable_linux_qt_backend() -> None:
    if not sys.platform.startswith("linux"):
        return

    # If a previous shell command exported xcb, Qt can abort before the app opens
    # when the system xcb dependencies are incomplete. Prefer Wayland by default.
    if os.environ.get("QT_QPA_PLATFORM") == "xcb" and os.environ.get("AI_NOTE_STUDIO_USE_XCB") != "1":
        os.environ.pop("QT_QPA_PLATFORM", None)


def main() -> int:
    _prefer_stable_linux_qt_backend()

    try:
        from PySide6 import QtGui, QtWidgets
    except ModuleNotFoundError:
        print("Brakuje zależności PySide6. Zainstaluj projekt poleceniem: pip install -e .[dev]")
        return 1

    from app.config import load_app_config
    from app.resources import asset_path
    from app.services import GeminiAIProvider, ImagePreparationService
    from app.storage import FileNoteRepository
    from app.ui import MainWindow
    from app.ui.onboarding_dialog import OnboardingDialog
    from app.ui.theme import apply_theme

    application = QtWidgets.QApplication(sys.argv)
    application.setApplicationName("Ink2Text")
    icon_path = asset_path("ink2text.ico")
    if icon_path.exists():
        application.setWindowIcon(QtGui.QIcon(str(icon_path)))
    apply_theme(application)

    repository = FileNoteRepository()
    app_config = load_app_config(base_dir=repository.base_dir, env_path=Path.cwd() / ".env")
    if not app_config.onboarding_completed:
        onboarding_dialog = OnboardingDialog(app_config, app_config.app_language)
        if not application.windowIcon().isNull():
            onboarding_dialog.setWindowIcon(application.windowIcon())
        if onboarding_dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            from app.config import save_app_config

            save_app_config(
                app_config.config_path,
                gemini_api_key=onboarding_dialog.api_key,
                gemini_model=onboarding_dialog.model_name,
                app_language=onboarding_dialog.app_language,
                onboarding_completed=True,
                store_api_key_securely=True,
            )
            app_config = load_app_config(base_dir=repository.base_dir, env_path=Path.cwd() / ".env")

    image_preparation_service = ImagePreparationService(base_dir=repository.base_dir)
    ai_provider = GeminiAIProvider(
        api_key=app_config.gemini_api_key,
        model_name=app_config.gemini_model,
        config_path=app_config.config_path,
        language=app_config.app_language,
    )
    window = MainWindow(
        repository=repository,
        image_preparation_service=image_preparation_service,
        ai_provider=ai_provider,
        app_config=app_config,
    )
    if not application.windowIcon().isNull():
        window.setWindowIcon(application.windowIcon())
    if sys.platform.startswith("linux") and os.environ.get("WAYLAND_DISPLAY"):
        screen = application.primaryScreen()
        if screen is not None:
            available_height = screen.availableGeometry().height()
            if available_height > 0:
                max_height = max(720, available_height - 48)
                if window.minimumHeight() > max_height:
                    window.setMinimumHeight(max_height)
                window.setMaximumHeight(max_height)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
