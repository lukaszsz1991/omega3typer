import secrets
from django.db import models
from django.contrib.auth.models import AbstractUser


# ---------------------------------------------------------
# UŻYTKOWNIK
# ---------------------------------------------------------
# Rozszerzamy wbudowany model User Django o pole avatar (WF-04).
# Hasła są automatycznie hashowane przez Django (spełnia WNF-10).
class User(AbstractUser):
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    def __str__(self):
        return self.username


# ---------------------------------------------------------
# SPORT
# ---------------------------------------------------------
class Sport(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


# ---------------------------------------------------------
# DRUŻYNA
# ---------------------------------------------------------
class Team(models.Model):
    name = models.CharField(max_length=100)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="teams")

    def __str__(self):
        return self.name


# ---------------------------------------------------------
# LIGA (prywatna lub globalna)
# ---------------------------------------------------------
class League(models.Model):
    name = models.CharField(max_length=100)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="leagues")
    is_private = models.BooleanField(default=False)
    invite_code = models.CharField(max_length=20, unique=True, blank=True, null=True)

    # M2M przez tabelę pośredniczącą LeagueMember (WF-20, WF-21, WF-23, WF-24)
    members = models.ManyToManyField(
        User, through="LeagueMember", related_name="leagues"
    )

    def save(self, *args, **kwargs):
        # Automatyczne generowanie kodu zaproszenia dla lig prywatnych
        if self.is_private and not self.invite_code:
            self.invite_code = secrets.token_urlsafe(8)[:20]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ---------------------------------------------------------
# CZŁONKOSTWO W LIDZE (tabela pośrednicząca User <-> League)
# ---------------------------------------------------------
class LeagueMember(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "league")  # użytkownik nie dołącza 2x do tej samej ligi

    def __str__(self):
        return f"{self.user} w {self.league}"


# ---------------------------------------------------------
# MECZ
# ---------------------------------------------------------
class Match(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Zaplanowany"
        LIVE = "live", "W trakcie"
        FINISHED = "finished", "Zakończony"

    class Result(models.TextChoices):
        HOME = "home_win", "Wygrana gospodarzy"
        DRAW = "draw", "Remis"
        AWAY = "away_win", "Wygrana gości"

    league = models.ForeignKey(League, on_delete=models.CASCADE, related_name="matches")
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="home_matches")
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="away_matches")
    scheduled_at = models.DateTimeField()
    home_score = models.PositiveSmallIntegerField(blank=True, null=True)
    away_score = models.PositiveSmallIntegerField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED
    )
    result = models.CharField(
        max_length=20, choices=Result.choices, blank=True, null=True
    )

    def save(self, *args, **kwargs):
        # Automatyczne wyliczenie wyniku na podstawie bramek (tylko gdy oba wpisane)
        if self.home_score is not None and self.away_score is not None:
            if self.home_score > self.away_score:
                self.result = self.Result.HOME
            elif self.away_score > self.home_score:
                self.result = self.Result.AWAY
            else:
                self.result = self.Result.DRAW
        super().save(*args, **kwargs)

    @property
    def is_locked(self):
        """Blokada typowania po rozpoczęciu meczu (WF-14, WNF-13)."""
        return self.status != self.Status.SCHEDULED

    def __str__(self):
        if self.status == self.Status.FINISHED:
            return f"{self.home_team} {self.home_score}:{self.away_score} {self.away_team}"
        else:
            return f"{self.home_team} - {self.away_team} ({self.scheduled_at:%d-%m-%Y})"


# ---------------------------------------------------------
# TYP (PREDICTION)
# ---------------------------------------------------------
class Prediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="predictions")
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="predictions")
    predicted_home = models.PositiveIntegerField()
    predicted_away = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "match")  # jeden typ na mecz na użytkownika

    def __str__(self):
        return f"{self.user} -> {self.match}: {self.predicted_home}:{self.predicted_away}"


# ---------------------------------------------------------
# PUNKTY
# ---------------------------------------------------------
# Powiązane 1-do-1 z Prediction (user i match odczytujemy przez prediction,
# więc nie duplikujemy tych kolumn jak w oryginalnym ERD).
class Points(models.Model):
    prediction = models.OneToOneField(
        Prediction, on_delete=models.CASCADE, related_name="points"
    )
    points_awarded = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.prediction} -> {self.points_awarded} pkt"
