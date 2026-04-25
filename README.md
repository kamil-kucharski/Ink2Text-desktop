# Notatki AI Desktop

Aplikacja desktopowa w Pythonie do zamiany zdjęć odręcznych notatek na czytelne, edytowalne notatki tekstowe z możliwością zapisu lokalnego i eksportu do PDF.

## Status projektu

Repozytorium zawiera pierwszy działający szkielet aplikacji desktopowej bez integracji AI.

## Główne założenia

- desktop-first w Pythonie
- docelowy build do pliku `.exe`
- analiza zdjęć notatek przez model AI
- lokalne przechowywanie notatek
- edycja i eksport do PDF
- publiczny rozwój projektu na GitHubie

## Planowany stack

- `Python`
- `PySide6`
- `OpenAI API`
- `SQLite`
- `Markdown`
- `PyInstaller`
- `pytest`

## Struktura repozytorium

```text
.
├── .github/
├── app/
│   ├── core/
│   ├── models/
│   ├── resources/
│   ├── services/
│   ├── storage/
│   └── ui/
├── docs/
├── scripts/
├── tests/
│   ├── integration/
│   └── unit/
├── .env.example
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── pyproject.toml
└── README.md
```

## Dokumentacja

- [Przewodnik użytkownika](docs/user-guide.md)
- [Przewodnik deweloperski](docs/developer-guide.md)
- [Architektura](docs/architecture.md)
- [Strategia testów](docs/testing.md)
- [Proces wydawniczy](docs/release.md)

## Najbliższe kroki

1. Dodać import zdjęć do notatki.
2. Zaimplementować pipeline przygotowania obrazów.
3. Podłączyć warstwę AI do transkrypcji.
4. Dodać eksport do PDF.
5. Przygotować build `.exe`.

## Obecna funkcjonalność

- uruchamianie aplikacji desktopowej
- tworzenie nowej notatki
- edycja tytułu i treści
- zapis lokalny do plików JSON
- odczyt i lista zapisanych notatek

## Uruchomienie lokalne

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python3 -m app
```

Na Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
python -m app
```
