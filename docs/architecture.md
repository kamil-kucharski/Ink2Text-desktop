# Architektura

## Kierunek architektoniczny

Projekt jest planowany jako aplikacja desktopowa w Pythonie z lokalnym przechowywaniem danych i zewnętrzną integracją AI do analizy obrazów.

## Moduły

- `app/ui` odpowiada za interfejs użytkownika
- `app/core` odpowiada za logikę domenową
- `app/services` odpowiada za integracje z usługami zewnętrznymi i przetwarzanie
- `app/storage` odpowiada za zapis danych i plików
- `app/models` odpowiada za modele danych
- `app/resources` zawiera zasoby aplikacji

## Docelowe przepływy

1. Użytkownik dodaje jedno lub wiele zdjęć.
2. Aplikacja przygotowuje obrazy do analizy.
3. Warstwa AI generuje uporządkowaną transkrypcję.
4. Użytkownik edytuje i zapisuje notatkę.
5. Notatka może zostać wyeksportowana do PDF.

