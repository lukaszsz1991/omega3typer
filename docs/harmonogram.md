# Harmonogram realizacji pracy inżynierskiej

## Aplikacja webowa do typowania wyników wydarzeń sportowych (Django)

_Stan na 10.10.2026. Zaznaczone `[x]` = zrobione, `[ ]` = do zrobienia._

## Marzec

### Tydzień 1 – Analiza i projekt systemu

- [x] Określenie wymagań funkcjonalnych:
  - [x] rejestracja i logowanie użytkowników
  - [x] tworzenie wydarzeń sportowych
  - [x] typowanie wyników
  - [x] system punktacji
  - [x] ranking użytkowników
- [x] Projekt bazy danych (diagram ERD):
  - [x] User
  - [x] Sport
  - [x] League
  - [x] Team
  - [x] Match
  - [x] Prediction
  - [x] Points
- [x] Wybór technologii:
  - [x] Django
  - [x] PostgreSQL
  - [x] Bootstrap (frontend)

**Rezultat:** gotowy projekt techniczny i model danych.

---

### Tydzień 2–3 – Implementacja backendu

- [x] Implementacja modeli Django:
  - [x] Team
  - [x] Match
  - [x] Prediction
  - [x] Points
- [x] Konfiguracja panelu administratora
- [x] System rejestracji i logowania
- [x] Dodawanie i edycja meczów (na razie przez panel admina)
- [x] Dodawanie typów przez użytkownika
- [x] Blokada typowania po rozpoczęciu meczu

**Rezultat:** działający system umożliwiający typowanie wyników.

---

### Tydzień 4 – System punktacji i ranking

- [x] Logika przyznawania punktów:
  - [x] dokładny wynik (4 pkt)
  - [x] ta sama różnica bramek (2 pkt)
  - [x] trafiony zwycięzca (1 pkt)
- [x] Automatyczne naliczanie punktów po zakończeniu meczu
- [x] Prosty ranking użytkowników

### Kamień milowy #1

Działające MVP backendowe:

- [x] logowanie
- [x] dodawanie meczów
- [x] typowanie
- [x] naliczanie punktów
- [x] ranking

---

## Kwiecień

### Tydzień 5–6 – Frontend i interfejs użytkownika

- [x] Strona główna z listą meczów
- [ ] Widok szczegółów meczu
- [x] Formularz typowania
- [x] Widok rankingu
- [ ] Responsywność aplikacji (jest Bootstrap, brak przeglądu na telefonie)
- [ ] Filtrowanie meczów (sport, liga)

---

### Tydzień 7 – System lig prywatnych

- [ ] Tworzenie prywatnych lig (w kodzie: `TypingGroup`)
- [ ] Dołączanie do ligi przez kod
- [ ] Ranking w obrębie ligi
- [ ] Panel zarządzania ligą

---

### Tydzień 8 – Automatyzacja i API

- [ ] Integracja z zewnętrznym API sportowym (opcjonalnie)
- [ ] Automatyczne pobieranie meczów
- [ ] Wystawienie REST API (opcjonalnie)

### Kamień milowy #2

Rozbudowana aplikacja:

- [ ] prywatne ligi
- [x] ranking globalny
- [ ] ligowy (globalny jest, ligowego brak)
- [ ] dopracowany frontend
- [ ] automatyzacja danych (opcjonalnie)

---

## Maj

### Tydzień 9 – Testy

- [ ] Testy jednostkowe modeli (częściowo: `is_locked`, `result`, punkty)
- [x] Testy logiki punktacji
- [ ] Testy widoków (częściowo: tylko `predict_view`)
- [x] Weryfikacja poprawności naliczania punktów

---

### Tydzień 10 – Bezpieczeństwo

- [ ] Walidacja danych wejściowych (częściowo: formularze Django)
- [x] Ochrona przed modyfikacją typów po starcie meczu
- [ ] Kontrola uprawnień użytkowników (częściowo: `login_required`)

---

### Tydzień 11 – Deployment

- [ ] Konfiguracja środowiska produkcyjnego
- [ ] Wdrożenie aplikacji
- [ ] Konfiguracja bazy danych

---

### Tydzień 12 – Refaktoryzacja i poprawki

- [ ] Optymalizacja zapytań do bazy danych
- [ ] Poprawa struktury kodu
- [ ] Ulepszenia interfejsu użytkownika
- [ ] Przygotowanie projektu do oddania

### Kamień milowy #3

Gotowa aplikacja:

- [ ] działająca online
- [ ] przetestowana
- [ ] zabezpieczona
- [ ] przygotowana do opisania w dokumentacji

---

# SEMESTR 2 – Dokumentacja i finalizacja

- [ ] Opis wymagań funkcjonalnych i niefunkcjonalnych
- [ ] Diagramy UML
- [ ] Opis architektury systemu
- [ ] Opis technologii
- [ ] Opis testów
- [ ] Wnioski końcowe
- [ ] Poprawki po uwagach promotora

---

# Podsumowanie

Po pierwszym semestrze system powinien być ukończony w ~70%  
Drugi semestr przeznaczony głównie na dokumentację i dopracowanie szczegółów.