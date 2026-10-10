import secrets
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from .constants import POINTS_WINNER, POINT_GOAL_DIFFERENCE, POINTS_EXACT_SCORE, NO_POINTS

class User(AbstractUser):
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    def __str__(self):
        return self.username


class Sport(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Team(models.Model):
    name = models.CharField(max_length=100)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="teams")

    def __str__(self):
        return self.name

class League(models.Model):
    name = models.CharField(max_length=100)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name="leagues")

    def __str__(self):
        return self.name

class TypingGroup(models.Model):
    name = models.CharField(max_length=100)
    is_private = models.BooleanField(default=False)
    invite_code = models.CharField(max_length=20, unique=True, blank=True, null=True)

    members = models.ManyToManyField(
        User, through="TypingGroupMember", related_name="typing_groups"
    )

    def save(self, *args, **kwargs):
        if self.is_private and not self.invite_code:
            self.invite_code = secrets.token_urlsafe(8)[:20]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TypingGroupMember(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(TypingGroup, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "group")  # użytkownik nie dołącza 2x do tej samej grupy

    def __str__(self):
        return f"{self.user} w {self.group}"

def outcome(home, away):
    if home > away:
        return "home"
    if away > home:
        return "away"
    return "draw"

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
        if self.home_score is not None and self.away_score is not None:
            if self.home_score > self.away_score:
                self.result = self.Result.HOME
            elif self.away_score > self.home_score:
                self.result = self.Result.AWAY
            else:
                self.result = self.Result.DRAW
        super().save(*args, **kwargs)
        if (
            self.status == self.Status.FINISHED
            and self.home_score is not None
            and self.away_score is not None
        ):
            for prediction in self.predictions.all():
                prediction.calculate_points()

    @property
    def is_locked(self):
        return (self.status != self.Status.SCHEDULED or timezone.now() >= self.scheduled_at)

    def __str__(self):
        if self.status == self.Status.FINISHED:
            return f"{self.home_team} {self.home_score}:{self.away_score} {self.away_team}"
        else:
            return f"{self.home_team} - {self.away_team} ({self.scheduled_at:%d-%m-%Y})"


class Prediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="predictions")
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="predictions")
    predicted_home = models.PositiveSmallIntegerField()
    predicted_away = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "match")  # jeden typ na mecz na użytkownika

    def __str__(self):
        return f"{self.user} -> {self.match}: {self.predicted_home}:{self.predicted_away}"

    def calculate_points(self):
        match = self.match
        if (self.predicted_home == match.home_score and self.predicted_away == match.away_score):
            value = POINTS_EXACT_SCORE
        elif (self.predicted_home - self.predicted_away == match.home_score - match.away_score):
            value = POINT_GOAL_DIFFERENCE
        elif outcome(self.predicted_home, self.predicted_away) == outcome(match.home_score, match.away_score):
            value = POINTS_WINNER
        else:
            value = NO_POINTS
        Points.objects.update_or_create(prediction=self, defaults={"points_awarded": value})


class Points(models.Model):
    prediction = models.OneToOneField(
        Prediction, on_delete=models.CASCADE, related_name="points"
    )
    points_awarded = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.prediction} -> {self.points_awarded} pkt"