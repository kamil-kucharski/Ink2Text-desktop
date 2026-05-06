<p align="center">
  <img src="assets/logoink2text_full.png" alt="Logo Ink2Text" width="100">
</p>

<h1 align="center">Ink2Text</h1>

<p align="center">
  Nowoczesna aplikacja desktopowa do zamiany zdjęć odręcznych notatek w czysty, edytowalny i estetycznie sformatowany tekst.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-172B65?style=for-the-badge&logo=python&logoColor=white">
  <img alt="PySide6" src="https://img.shields.io/badge/PySide6-Desktop_UI-172B65?style=for-the-badge">
  <img alt="Gemini" src="https://img.shields.io/badge/Gemini-Notatki_AI-172B65?style=for-the-badge">
  <img alt="Platforma" src="https://img.shields.io/badge/Windows_EXE-gotowe-172B65?style=for-the-badge&logo=windows&logoColor=white">
</p>

<p align="center">
  <a href="README.md">English README</a>
</p>

---

## Podgląd

<p align="center">
  <img src="docs/screenshots/main-window.png" alt="Podgląd głównego okna Ink2Text" width="900">
  <br>
  <sub>Główny ekran do importu zdjęć, generowania notatek, edycji tekstu i zarządzania lokalnymi notatkami.</sub>
</p>

<p align="center">
  <img src="docs/screenshots/ai-settings.png" alt="Podgląd ustawień AI Ink2Text" width="420">
  <br>
  <sub>Ustawienia AI do konfiguracji klucza Gemini, modelu i języka aplikacji.</sub>
</p>

<p align="center">
  <img src="docs/screenshots/pdf-preview.png" alt="Podgląd PDF Ink2Text" width="420">
  <br>
  <sub>Podgląd PDF pozwalający sprawdzić finalny dokument przed eksportem.</sub>
</p>

<br>

## Pobieranie

Gotowy plik wykonywalny dla Windows jest dostępny w sekcji **Releases**.

> Uwaga: Windows SmartScreen może wyświetlić ostrzeżenie, ponieważ aplikacja nie jest podpisana cyfrowo.

<br>

## O Projekcie

Ink2Text to aplikacja desktopowa, która pomaga zamienić odręczne notatki ze zdjęć w czytelne notatki cyfrowe. Użytkownik importuje jedno lub kilka zdjęć, wybiera tryb AI, generuje notatkę, poprawia ją w edytorze tekstu i eksportuje gotowy efekt do PDF.

Projekt został przygotowany jako kompletna aplikacja desktopowa oparta o realny przepływ pracy użytkownika: import odręcznych materiałów, przetwarzanie ich przez AI, edycję wyniku, lokalne przechowywanie notatek i eksport do estetycznego PDF.

<br>

## Dlaczego Powstał Ten Projekt

Odręczne notatki nadal są szybkie, wygodne i naturalne, ale trudno je przeszukiwać, edytować oraz udostępniać. Ink2Text powstał po to, żeby połączyć wygodę pisania ręcznego z możliwością późniejszej pracy na uporządkowanym dokumencie cyfrowym.

<br>

## Najważniejsze Funkcje

- Import jednego lub wielu zdjęć odręcznych notatek.
- Zmiana kolejności zdjęć metodą przeciągnij i upuść.
- Generowanie edytowalnych notatek przez Gemini AI.
- Wybór trybu transkrypcji, formatowania, uporządkowania lub rozszerzenia notatki.
- Zachowanie języka oryginalnej notatki ze zdjęcia.
- Edycja wygenerowanej treści w edytorze rich text.
- Podgląd i eksport notatek do estetycznego pliku PDF.
- Lokalne przechowywanie notatek na komputerze użytkownika.
- Nowoczesny, minimalistyczny interfejs desktopowy.
- Możliwość zbudowania aplikacji jako pliku `.exe` na Windows.

<br>

## Tryby AI

| Tryb | Zastosowanie |
| --- | --- |
| Wierna transkrypcja | Przepisuje tekst ze zdjęcia bez poprawiania i formatowania. |
| Formatowanie notatki | Dodaje strukturę, nagłówki, odstępy i czytelne formatowanie. |
| Uporządkowanie notatki | Poprawia styl, gramatykę i czytelność, zachowując sens notatki. |
| Rozszerzenie notatki | Ulepsza notatkę i może dodać przydatne wyjaśnienia w kontrolowanym zakresie. |

<br>

## Technologie

| Obszar | Technologia |
| --- | --- |
| Język | Python 3.12 |
| Interfejs desktopowy | PySide6 / Qt |
| AI | Google Gemini |
| Obsługa obrazów | Pillow |
| Eksport PDF | Renderowanie rich text przez Qt |
| Budowanie aplikacji | PyInstaller |
| Testy | pytest |

<br>

## Czego Się Nauczyłem

Ink2Text był dobrym ćwiczeniem w budowaniu aplikacji desktopowej jako kompletnego produktu, a nie tylko technicznego demo. Najważniejsze elementy tego procesu to:

- Podzielenie kodu Pythonowego na czytelne warstwy: komponenty UI, serwisy, storage, modele, konfigurację i skrypty buildowania.
- Praca z PySide6 wykraczająca poza podstawowe widgety, czyli własne komponenty, wspólny styl, lokalizacja tekstów i zachowanie spójne na Linuxie oraz Windowsie.
- Zaprojektowanie workflow AI, które jest przewidywalne dla użytkownika: uporządkowane prompty, zachowanie języka źródłowego, ponawianie zapytań, fallback modeli, obsługa klucza API i czytelne błędy.
- Podejście local-first, w którym notatki, ustawienia i wrażliwa konfiguracja zostają na komputerze użytkownika zamiast wymagać zewnętrznego backendu.
- Połączenie kilku typowo desktopowych przepływów w jednym miejscu: import obrazów, zmiana kolejności drag-and-drop, edycja rich text, podgląd PDF i renderowanie PDF.

<br>

## Uruchomienie Projektu

### 1. Sklonowanie repozytorium

```bash
git clone https://github.com/kamil-kucharski/Ink2Text.git
cd Ink2Text
```

### 2. Utworzenie i aktywowanie środowiska wirtualnego

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Zainstalowanie zależności

```bash
pip install -e ".[dev,build]"
```

### 4. Uruchomienie aplikacji

```bash
python -m app
```

<br>

## Klucz API Gemini

Ink2Text używa Gemini do generowania notatek przez AI. Przy pierwszym uruchomieniu aplikacja poprosi o skonfigurowanie klucza API w ustawieniach lub ekranie startowym.

Klucz API Gemini można utworzyć w Google AI Studio:

```text
https://aistudio.google.com/app/apikey
```

<br>

## Przykładowe Notatki

Repozytorium zawiera folder `sample_notes/` z przykładowymi zdjęciami notatek, które można wykorzystać do testowania aplikacji po uruchomieniu jej z kodu.

Możesz otworzyć aplikację, zaimportować przykładowe zdjęcia, wybrać tryb AI i wygenerować notatkę bez przygotowywania własnych materiałów.

<br>

## Budowanie Pliku EXE Na Windows

Na Windows, po zainstalowaniu zależności, uruchom:

```powershell
python scripts\build_windows_exe.py
```

Gotowa aplikacja będzie dostępna w:

```text
dist\Ink2Text\Ink2Text.exe
```

<br>

## Testy

```bash
pytest
```

<br>

## Struktura Projektu

```text
app/
  services/        AI, eksport PDF, przygotowanie obrazów
  storage/         Lokalne przechowywanie notatek
  ui/              Interfejs PySide6 i komponenty UI
  models/          Model danych notatki
assets/            Ikony i grafiki aplikacji
sample_notes/      Przykładowe notatki do testów
scripts/           Skrypty budowania aplikacji
tests/             Testy jednostkowe i integracyjne
```

<br>

## Prywatność

Ink2Text przechowuje notatki i ustawienia lokalnie. Zdjęcia oraz treść notatek są wysyłane do skonfigurowanego dostawcy AI tylko wtedy, gdy użytkownik świadomie generuje notatkę.

<br>

## Autor

Autor projektu: **Kamil Kucharski**
