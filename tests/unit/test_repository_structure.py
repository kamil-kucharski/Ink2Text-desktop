from pathlib import Path


def test_repository_scaffold_exists() -> None:
    root = Path(__file__).resolve().parents[2]

    expected_paths = [
        root / "README.md",
        root / "pyproject.toml",
        root / "docs" / "architecture.md",
        root / "tests" / "integration",
        root / "app" / "ui",
        root / ".github" / "workflows" / "ci.yml",
    ]

    for path in expected_paths:
        assert path.exists()

