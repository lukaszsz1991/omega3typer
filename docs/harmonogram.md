# Harmonogram realizacji pracy inżynierskiej

## Aplikacja webowa do typowania wyników wydarzeń sportowych (Django)

_Stan na 13.10.2026._

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
- [x] Lista rozgrywek i strona ligi z meczami (nadchodzące i zakończone)
- [x] Publiczny dostęp bez logowania: lista meczów, szczegóły meczu, ranking
- [x] Widok szczegółów meczu (typ użytkownika, punkty, typy graczy po starcie meczu)
- [x] Formularz typowania
- [x] Widok rankingu (na razie globalny)
- [x] Responsywność aplikacji
- [ ] Rankingi poszczególnych lig na stronie ligi (zamiast rankingu globalnego)

- [ ] Filtrowanie meczów (częściowo: podział na ligi)
- [ ] Podział meczów na kolejki

---

### Tydzień 7 – System grup prywatnych

- [x] Tworzenie prywatnych grup (w kodzie: `TypingGroup`) z wyborem ligi
- [x] Dołączanie do grupy przez kod
- [x] Ranking w obrębie grupy (punkty tylko z meczów ligi grupy)
- [x] Archiwizacja grup po zakończeniu sezonu (blokada dołączania)
- [x] Panel zarządzania grupą (usuwanie członków, zmiana kodu, opuszczanie grupy)

---

### Tydzień 8 – Automatyzacja i API

- [x] Import drużyn i meczów z pliku CSV (komenda zarządzająca)
- [ ] Integracja z zewnętrznym API sportowym (opcjonalnie)
- [ ] Automatyczne pobieranie meczów (opcjonalnie)
- [ ] Wystawienie REST API (opcjonalnie)

### Kamień milowy #2

Rozbudowana aplikacja:

- [x] prywatne grupy
- [x] ranking globalny
- [x] ranking ligowy (w grupie, liczony z meczów jej ligi)
- [ ] dopracowany frontend
- [ ] automatyzacja danych (opcjonalnie)

---

## Maj

### Tydzień 9 – Testy

- [ ] Testy jednostkowe modeli (częściowo: `is_locked`, `result`, punkty, walidacja meczu)
- [x] Testy logiki punktacji
- [ ] Testy widoków (częściowo: typowanie, grupy, ligi, lista i szczegóły meczu)
- [x] Weryfikacja poprawności naliczania punktów

---

### Tydzień 10 – Bezpieczeństwo

- [x] Ochrona przed modyfikacją typów po starcie meczu
- [x] Typy i punkty tylko do odczytu w panelu administratora
- [x] Typy innych graczy ukryte do startu meczu
- [x] Konfiguracja z pliku .env (SECRET_KEY, DEBUG, ALLOWED_HOSTS, EMAIL_BACKEND).
- [ ] Walidacja danych wejściowych (częściowo: formularze Django, `Match.clean`, unikalność drużyn w sporcie)
- [ ] Kontrola uprawnień użytkowników (częściowo: `login_required`, strona grupy tylko dla członków, akcje właściciela grupy)

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