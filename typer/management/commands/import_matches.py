import csv
import re
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from typer.models import League, Match, Team


def plain(name):
    """Nazwa bez flagi/emotek i spacji na początku i końcu, bez różnic wielkości liter."""
    return re.sub(r"^[^\w]+|[^\w]+$", "", name).strip().casefold()


def find_league(name, year):
    wanted = plain(name)
    for league in League.objects.select_related("sport").filter(year=year):
        if plain(league.name) == wanted:
            return league
    raise League.DoesNotExist


class Command(BaseCommand):
    help = (
        "Importuje mecze z pliku CSV. Kolumny: league, year, home_team, away_team, "
        "scheduled_at (RRRR-MM-DD GG:MM), home_score, away_score (puste dla meczów przyszłych)."
    )

    def add_arguments(self, parser):
        parser.add_argument("path", help="Ścieżka do pliku CSV")
        parser.add_argument("--delimiter", default=",", help="Separator kolumn (domyślnie ,)")

    @transaction.atomic
    def handle(self, *args, **options):
        created = updated = 0
        with open(options["path"], newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=options["delimiter"])
            for number, row in enumerate(reader, start=2):
                try:
                    league = find_league(row["league"], int(row["year"]))
                    home, _ = Team.objects.get_or_create(sport=league.sport, name=row["home_team"].strip())
                    away, _ = Team.objects.get_or_create(sport=league.sport, name=row["away_team"].strip())
                    when = timezone.make_aware(
                        datetime.strptime(row["scheduled_at"].strip(), "%Y-%m-%d %H:%M")
                    )
                    defaults = {}
                    home_score = (row.get("home_score") or "").strip()
                    away_score = (row.get("away_score") or "").strip()
                    if home_score and away_score:
                        defaults = {
                            "home_score": int(home_score),
                            "away_score": int(away_score),
                            "status": Match.Status.FINISHED,
                        }
                    _, was_created = Match.objects.update_or_create(
                        league=league, home_team=home, away_team=away,
                        scheduled_at=when, defaults=defaults,
                    )
                except League.DoesNotExist:
                    available = ", ".join(f"{l.name} {l.year}" for l in League.objects.all())
                    raise CommandError(
                        f"Wiersz {number}: nie ma ligi „{row['league']}” z rokiem {row['year']}. "
                        f"Dostępne: {available}"
                    )
                except (KeyError, ValueError) as error:
                    raise CommandError(f"Wiersz {number}: {error!r}")
                created += was_created
                updated += not was_created
        self.stdout.write(self.style.SUCCESS(f"Gotowe: dodano {created}, zaktualizowano {updated}."))