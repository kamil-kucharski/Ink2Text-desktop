from __future__ import annotations

import sys


def main() -> int:
    try:
        from PySide6 import QtWidgets
    except ModuleNotFoundError:
        print("Brakuje zależności PySide6. Zainstaluj projekt poleceniem: pip install -e .[dev]")
        return 1

    from app.config import load_app_config
    from app.services import GeminiAIProvider, ImagePreparationService
    from app.storage import FileNoteRepository
    from app.ui import MainWindow
    from app.ui.theme import apply_theme

    application = QtWidgets.QApplication(sys.argv)
    application.setApplicationName("Notatki AI Desktop")
    apply_theme(application)

    repository = FileNoteRepository()
    app_config = load_app_config(base_dir=repository.base_dir)
    image_preparation_service = ImagePreparationService(base_dir=repository.base_dir)
    ai_provider = GeminiAIProvider(
        api_key=app_config.gemini_api_key,
        model_name=app_config.gemini_model,
        config_path=app_config.config_path,
    )
    window = MainWindow(
        repository=repository,
        image_preparation_service=image_preparation_service,
        ai_provider=ai_provider,
        app_config=app_config,
    )
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
