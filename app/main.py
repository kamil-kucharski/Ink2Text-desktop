from __future__ import annotations

import sys


def main() -> int:
    try:
        from PySide6 import QtWidgets
    except ModuleNotFoundError:
        print("Brakuje zależności PySide6. Zainstaluj projekt poleceniem: pip install -e .[dev]")
        return 1

    from app.storage import FileNoteRepository
    from app.ui import MainWindow

    application = QtWidgets.QApplication(sys.argv)
    application.setApplicationName("Notatki AI Desktop")

    window = MainWindow(repository=FileNoteRepository())
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())

