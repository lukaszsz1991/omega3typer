# Dla administratora

Administrator przygotowuje dane, na których grają użytkownicy: sporty, rozgrywki, drużyny i mecze,
a po meczach wpisuje wyniki. Służy do tego panel administratora pod adresem `/admin/`
(np. <http://127.0.0.1:8000/admin/> w przypadku uruchomienia lokalnego). Konto administratora zakładasz poleceniem:

```bash
python manage.py createsuperuser
```

## Dodawanie i edycja danych

Dane dodawaj w tej kolejności, bo każdy następny element wymaga poprzedniego:

1. **Sport** (np. „Piłka nożna”). Nazwa musi być unikalna.
2. **Rozgrywki** (liga lub turniej): nazwa, sport, rok i data zakończenia. Para *nazwa + rok* musi być
   unikalna. Data zakończenia decyduje, kiedy sezon się kończy i grupy tych rozgrywek trafiają do archiwum
   (zob. [Dla gracza](gracz.md#grupy-prywatne)).
3. **Drużyny**: nazwa i sport. Nazwa drużyny jest unikalna w obrębie sportu, więc ta sama nazwa może
   wystąpić w dwóch różnych sportach.
4. **Mecze**: rozgrywki, gospodarz, gość, termin, a opcjonalnie kolejka, a także bramki gospodarzy i gości dla meczów
   zakończonych.

Przy zapisie meczu panel sprawdza, że gospodarz i gość to dwie różne drużyny oraz że obie grają w tym
samym sporcie co rozgrywki. Nowy mecz ma status „Zaplanowany” i od tej chwili gracze mogą go typować.

Drużyny i mecze możesz też dodać hurtowo [importem z pliku CSV](#import-meczów-z-pliku-csv).
Typy i punkty graczy są w panelu tylko do podglądu: nie można ich dodawać ani zmieniać.

> Zmiana terminu meczu przesuwa też moment zablokowania typowania. Nie przenoś meczu na później,
> jeśli gracze już typują, a mecz miał się wkrótce zacząć, bez powiadomienia ich o tym.

## Wpisywanie wyników

Wynik wpisujesz w panelu, w edycji meczu:

1. Wypełnij pola **Home score** i **Away score** (bramki gospodarzy i gości).
2. Ustaw **Status** na „Zakończony”.
3. Zapisz mecz.

Przy zapisie aplikacja sama ustawia rezultat (wygrana gospodarzy, remis lub wygrana gości) i **od razu
nalicza punkty wszystkim graczom**, którzy wytypowali ten mecz. Nie ma osobnego kroku rozliczenia.
Zasady liczenia opisuje strona [Punktacja](gracz.md#punktacja).

Warto pamiętać o kilku rzeczach:

- **Punkty naliczają się tylko po zapisaniu obu wyników i statusu „Zakończony”.** Sam wynik bez zmiany
  statusu nie rozlicza typów.
- **Pomyłkę poprawisz, zmieniając wynik i zapisując mecz ponownie.** Punkty przeliczą się na nowo, bez
  duplikatów.
- **Zmiana statusu z powrotem na „Zaplanowany” nie usuwa przyznanych punktów.** Jeśli wpisałeś wynik
  przez pomyłkę, popraw go, zamiast cofać status.
- Status „W trakcie” jest dodatkowy i ustawiasz go ręcznie. Typowanie blokuje się samo o godzinie startu
  meczu, więc nie musisz go zmieniać, żeby zamknąć typowanie.
- Przy piłce ręcznej wpisuj wynik po 60 minutach, bez dogrywki.

## Import meczów z pliku CSV

Większą liczbę meczów łatwiej dodać z pliku niż ręcznie. Służy do tego polecenie:

```bash
python manage.py import_matches data/mecze_ekstraklasa2027.csv
```

Jeśli plik używa średnika zamiast przecinka (np. po zapisaniu z Excela), dodaj separator:

```bash
python manage.py import_matches dane.csv --delimiter ";"
```

### Format pliku

Plik jest w kodowaniu UTF-8, a pierwszy wiersz zawiera nazwy kolumn:

| Kolumna        | Opis                                                                                      | Wymagana |
|----------------|-------------------------------------------------------------------------------------------|----------|
| `league`       | nazwa rozgrywek, tak jak w panelu (wielkość liter i emotka flagi na początku są pomijane) | tak      |
| `year`         | rok rozgrywek, tak jak w panelu                                                           | tak      |
| `round`        | numer kolejki                                                                             | nie      |
| `home_team`    | gospodarz                                                                                 | tak      |
| `away_team`    | gość                                                                                      | tak      |
| `scheduled_at` | termin w formacie `RRRR-MM-DD GG:MM` (czas polski)                                        | tak      |
| `home_score`   | bramki gospodarzy, puste dla meczu przyszłego                                             | nie      |
| `away_score`   | bramki gości, puste dla meczu przyszłego                                                  | nie      |

Przykład:

```csv
league,year,round,home_team,away_team,scheduled_at,home_score,away_score
PKO BP Ekstraklasa,2027,1,Górnik Zabrze,Śląsk Wrocław,2026-07-25 17:30,2,1
PKO BP Ekstraklasa,2027,2,Lech Poznań,Cracovia,2026-08-01 20:15,,
```

Pierwszy wiersz to mecz zakończony (ma wynik), drugi to mecz do wytypowania (puste wyniki).

### Jak działa import

- **Rozgrywki muszą istnieć w panelu wcześniej.** Jeśli nie znajdzie rozgrywek o danej nazwie i roku,
  polecenie zatrzyma się i wypisze listę dostępnych.
- **Drużyny dodają się same**, w sporcie przypisanym do rozgrywek.
- **Mecz z wynikiem dostaje status „Zakończony”**, a typy graczy są od razu rozliczane.
- **Ponowny import jest bezpieczny.** Mecz znaleziony po rozgrywkach, drużynach i terminie jest
  aktualizowany, a nie dodawany drugi raz. Dzięki temu możesz dopisać wyniki, uruchamiając import tego
  samego pliku z uzupełnionymi kolumnami.
- **Zmiana terminu w pliku tworzy nowy mecz.** Termin jest częścią klucza, więc jeśli przesuniesz mecz,
  popraw go w panelu, a nie w pliku.
- **Import jest wszystko albo nic.** Jeśli któryś wiersz jest błędny (zła data, brak rozgrywek, wynik
  niebędący liczbą), nie zapisze się żaden mecz, a komunikat poda numer wiersza do poprawy.

Po zakończeniu polecenie wypisuje, ile meczów dodano i ile zaktualizowano.