"""Interfejs użytkownika aplikacji desktopowej."""

from app.ui.image_import import SUPPORTED_IMAGE_SUFFIXES, filter_supported_image_paths

__all__ = [
    "AISettingsDialog",
    "MainWindow",
    "SUPPORTED_IMAGE_SUFFIXES",
    "filter_supported_image_paths",
]


def __getattr__(name: str):
    if name == "MainWindow":
        from app.ui.main_window import MainWindow

        return MainWindow
    if name == "AISettingsDialog":
        from app.ui.settings_dialog import AISettingsDialog

        return AISettingsDialog
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
