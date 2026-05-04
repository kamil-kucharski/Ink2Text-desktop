from pathlib import Path


def test_repository_scaffold_exists() -> None:
    root = Path(__file__).resolve().parents[2]

    expected_paths = [
        root / "README.md",
        root / "pyproject.toml",
        root / "tests" / "integration",
        root / "app" / "ui",
        root / "app" / "ui" / "editor_toolbar.py",
        root / "app" / "ui" / "help_dialog.py",
        root / "app" / "ui" / "onboarding_dialog.py",
        root / "assets" / "ink2text.ico",
    ]

    for path in expected_paths:
        assert path.exists()
