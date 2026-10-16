# Najczęstsze pytania

## Konto

### Zapomniałem hasła. Co zrobić?

Na stronie logowania kliknij **Nie pamiętasz hasła?**, wpisz adres e-mail użyty przy rejestracji i sprawdź
skrzynkę. Link do ustawienia nowego hasła jest ważny przez 3 godziny. Szczegóły w sekcji
[Logowanie](gracz.md#logowanie).

### Nie dostałem e-maila z linkiem do zmiany hasła.

Sprawdź folder ze spamem. Wiadomość wysyłamy tylko na adres, którego użyłeś przy zakładaniu konta, więc
jeśli wpiszesz inny, nic nie przyjdzie. Gdy link wygaśnie, poproś o nowy.

### Czy mogę zmienić login lub adres e-mail?

Obecnie nie ma strony profilu, więc zmiana tych danych nie jest możliwa. Hasło możesz zmienić przez
procedurę przypominania hasła.

## Typowanie

### Dlaczego nie mogę zmienić ani dodać typu?

Typowanie meczu zamyka się w chwili jego rozpoczęcia i nie da się go już otworzyć. Typ możesz
zmieniać do godziny startu, potem jest niezmienny. Zasady opisuje sekcja
[Typowanie](gracz.md#typowanie).

### Dlaczego nie widzę meczu, który chcę wytypować?

Lista meczów pokazuje spotkania z **najbliższych 10 dni**. Mecz późniejszy pojawi się na liście, gdy
zbliży się jego termin. Sprawdź też filtry nad listą (sport i rozgrywki). Mogą ukrywać mecz, którego
szukasz.

### Czy muszę należeć do grupy, żeby typować?

Nie. Typować możesz każdy nadchodzący mecz, także rozgrywek, których nie ma w żadnej Twojej grupie.
Grupa decyduje tylko o tym, które mecze pojawiają się na górze listy i w jakim rankingu rywalizujesz ze
znajomymi.

### Kiedy zobaczę typy innych graczy?

Dopiero po rozpoczęciu meczu. Wcześniej są ukryte, żeby nikt nie mógł ich podejrzeć. Znajdziesz je na
stronie meczu.

## Punkty

### Kiedy dostanę punkty za typ?

Gdy administrator wpisze wynik i oznaczy mecz jako zakończony. Wtedy punkty naliczają się automatycznie
i widzisz je na stronie meczu przy swoim typie. Jeśli minęło sporo czasu od meczu, a punktów nadal nie
ma, mecz mógł nie zostać jeszcze rozliczony.

### Dlaczego dostałem mniej punktów, niż się spodziewałem?

Za jeden mecz dostajesz punkty tylko za **najwyżej punktowane trafione zdarzenie**. Punkty z różnych
kategorii się nie sumują. Tabele znajdziesz w sekcji [Punktacja](gracz.md#punktacja). Przy piłce ręcznej
liczy się wynik po 60 minutach, bez dogrywki.

### Czy remis jest trafiony, jeśli wytypowałem inną liczbę bramek?

Tak, w piłce nożnej daje to 2 punkty (taka sama różnica bramek, czyli 0). Dokładny wynik remisu daje 4
punkty. Zasady dla piłki ręcznej są inne i są opisane w tabeli w sekcji Punktacja.

### Administrator pomylił się w wyniku. Czy punkty się poprawią?

Tak. Po poprawieniu wyniku punkty wszystkich graczy przeliczają się automatycznie.

## Rankingi i grupy

### Czym różni się ranking rozgrywek od rankingu grupy?

Ranking rozgrywek jest publiczny i obejmuje wszystkich graczy typujących mecze tych rozgrywek. Ranking
grupy widzą tylko jej członkowie i liczy tylko punkty z meczów ligi, dla której grupę założono. Ten sam
typ liczy się w obu. Więcej w sekcji [Rankingi](gracz.md#rankingi).

### Kod zaproszenia nie działa.

Najczęstsze przyczyny to: literówka (kod rozróżnia wielkość liter), nowy kod wygenerowany przez
właściciela albo sezon rozgrywek grupy, który już się zakończył. Poproś właściciela o aktualny kod.

### Czy mogę opuścić grupę? Co się stanie z moimi punktami?

Możesz opuścić grupę w każdej chwili przyciskiem **Opuść grupę** na jej stronie. Twoje typy i punkty
zostają w rankingach rozgrywek, znikasz tylko z rankingu tej grupy. Właściciel grupy nie może jej
opuścić.

### Właściciel usunął mnie z grupy. Czy mogę wrócić?

Tak, jeśli znasz aktualny kod zaproszenia. Właściciel może go zmienić, żeby temu zapobiec. Zob.
[Zarządzanie członkami](wlasciciel.md#zarządzanie-członkami).

### Moja grupa jest w archiwum i nie mogę jej otworzyć.

Grupa trafia do archiwum następnego dnia po zakończeniu rozgrywek, dla których została założona. Nie
można już do niej dołączyć. Aby rywalizować w nowym sezonie, załóż nową grupę. Zob.
[Archiwizacja grupy](wlasciciel.md#archiwizacja-grupy).

## Dla administratora

### Wpisałem wynik, ale punkty się nie naliczyły.

Sprawdź, czy wypełnione są **oba pola wyniku** i czy status meczu to **„Zakończony”**. Punkty nalicza
dopiero zapis meczu z tym statusem. Zob. [Wpisywanie wyników](admin.md#wpisywanie-wyników).

### Import z CSV zatrzymał się z błędem.

Komunikat podaje numer wiersza z problemem. Najczęściej to brak rozgrywek w panelu (o takiej nazwie
i roku), zła data (poprawny format to `RRRR-MM-DD GG:MM`) albo wynik niebędący liczbą. Po poprawce
uruchom import jeszcze raz: nic z poprzedniej próby nie zostało zapisane. Zob.
[Import meczów z pliku CSV](admin.md#import-meczów-z-pliku-csv).