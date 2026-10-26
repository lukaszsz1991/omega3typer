# Omega 3 Typer

Aplikacja webowa do typowania wyników wydarzeń sportowych (praca inżynierska).POINTS_EXACT_SCORE = 4
POINTS_GOAL_DIFFERENCE = 2
POINTS_WINNER = 1
NO_POINTS = 0
Django + PostgreSQL + Bootstrap 5.

## Uruchomienie (Linux)

Instrukcja dla Ubuntu/Debian.

```bash
git clone https://github.com/lukaszsz1991/omega3typer.git
cd omega3typer
bash setup.sh
source venv/bin/activate
python manage.py createsuperuser
python manage.py runserver
```

Uruchomienie:

```bash
python manage.py runserver
```

### Skrypt instalacyjny `setup.sh`

Uruchom go w głównym folderze projektu (tam, gdzie leży `manage.py`):

```bash
bash setup.sh
```

Alternatywnie, po nadaniu uprawnień do wykonywania:

```bash
chmod +x setup.sh
./setup.sh
```

W trakcie skrypt poprosi o hasło `sudo` (to hasło Twojego konta w systemie). Instalacja
trwa kilka minut.

Skrypt instaluje potrzebne pakiety, tworzy środowisko wirtualne, zakłada bazę PostgreSQL,
generuje plik `.env` i wykonuje migracje. Można go uruchamiać ponownie, nie nadpisze
istniejącego `.env` ani bazy.

Aplikacja: <http://127.0.0.1:8000/>
Panel administratora: <http://127.0.0.1:8000/admin/>

## Testy

```bash
python manage.py test
```

## Import meczów z CSV

```bash
python manage.py import_matches data/mecze_ekstraklasa2027.csv
```

Kolumny: `league, year, round, home_team, away_team, scheduled_at, home_score, away_score`.
Liga musi istnieć w panelu (nazwa i rok, flaga w nazwie jest pomijana). Ponowny import aktualizuje istniejące mecze i
dopisuje wyniki.

## Plan prac

[docs/harmonogram.md](docs/harmonogram.md)