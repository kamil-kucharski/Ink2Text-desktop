from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    icon_path = project_root / "assets" / "ink2text.ico"
    assets_path = project_root / "assets"
    entrypoint = project_root / "app" / "__main__.py"

    if not icon_path.exists():
        print(f"Brak ikony aplikacji: {icon_path}")
        return 1

    try:
        from PyInstaller.__main__ import run
    except ModuleNotFoundError:
        print("Brakuje PyInstaller. Zainstaluj go poleceniem: pip install -e .[build]")
        return 1

    data_separator = ";" if os.name == "nt" else ":"
    run(
        [
            str(entrypoint),
            "--name",
            "Ink2Text",
            "--windowed",
            "--clean",
            "--noconfirm",
            "--icon",
            str(icon_path),
            "--add-data",
            f"{assets_path}{data_separator}assets",
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
