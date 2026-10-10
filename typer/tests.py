from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .constants import (
    POINTS_EXACT_SCORE,
    POINTS_GOAL_DIFFERENCE,
    POINTS_WINNER,
    NO_POINTS,
)
from .models import User, Sport, Team, League, Match, Prediction, Points, outcome


class OutcomeTests(TestCase):
    def test_outcome(self):
        self.assertEqual(outcome(2, 1), "home")
        self.assertEqual(outcome(0, 3), "away")
        self.assertEqual(outcome(1, 1), "draw")


class BaseTestCase(TestCase):
    """Wspólne dane: użytkownik, sport, drużyny, liga i mecz w przyszłości."""

    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="haslo-testowe-123")
        sport = Sport.objects.create(name="Piłka nożna")
        self.home = Team.objects.create(name="Drużyna A", sport=sport)
        self.away = Team.objects.create(name="Drużyna B", sport=sport)
        self.league = League.objects.create(name="Liga testowa", sport=sport)
        self.match = Match.objects.create(
            league=self.league,
            home_team=self.home,
            away_team=self.away,
            scheduled_at=timezone.now() + timedelta(days=1),
        )

    def predict(self, home, away):
        return Prediction.objects.create(
            user=self.user, match=self.match,
            predicted_home=home, predicted_away=away,
        )

    def finish(self, home, away):
        self.match.home_score = home
        self.match.away_score = away
        self.match.status = Match.Status.FINISHED
        self.match.save()


class PointsCalculationTests(BaseTestCase):
    def test_scoring_table(self):
        # (wynik meczu, typ, oczekiwane punkty)
        cases = [
            ((2, 1), (2, 1), POINTS_EXACT_SCORE),
            ((2, 1), (3, 2), POINTS_GOAL_DIFFERENCE),   # ta sama różnica
            ((2, 1), (1, 0), POINTS_GOAL_DIFFERENCE),
            ((2, 1), (3, 0), POINTS_WINNER),            # dobry zwycięzca, inna różnica
            ((2, 1), (1, 1), NO_POINTS),                # remis zamiast wygranej
            ((2, 1), (0, 1), NO_POINTS),                # zły zwycięzca
            ((1, 1), (1, 1), POINTS_EXACT_SCORE),       # dokładny remis
            ((2, 2), (1, 1), POINTS_GOAL_DIFFERENCE),   # trafiony remis, inny wynik
            ((1, 1), (2, 1), NO_POINTS),                # typ wygranej, był remis
        ]
        for (real_home, real_away), (pred_home, pred_away), expected in cases:
            with self.subTest(wynik=(real_home, real_away), typ=(pred_home, pred_away)):
                Prediction.objects.all().delete()  # kasuje też powiązane Points
                self.match.status = Match.Status.SCHEDULED
                self.match.home_score = None
                self.match.away_score = None
                self.match.save()

                prediction = self.predict(pred_home, pred_away)
                self.finish(real_home, real_away)

                self.assertEqual(prediction.points.points_awarded, expected)

    def test_no_points_before_match_finished(self):
        self.predict(2, 1)
        self.assertEqual(Points.objects.count(), 0)

    def test_no_points_when_finished_without_score(self):
        self.predict(2, 1)
        self.match.status = Match.Status.FINISHED
        self.match.save()  # brak wyniku, nie może się wywalić
        self.assertEqual(Points.objects.count(), 0)

    def test_resaving_match_does_not_duplicate_points(self):
        self.predict(2, 1)
        self.finish(2, 1)
        self.match.save()
        self.match.save()
        self.assertEqual(Points.objects.count(), 1)

    def test_correcting_score_updates_points(self):
        prediction = self.predict(2, 1)
        self.finish(2, 1)
        self.assertEqual(prediction.points.points_awarded, POINTS_EXACT_SCORE)

        self.finish(0, 3)  # korekta wyniku
        prediction.points.refresh_from_db()
        self.assertEqual(prediction.points.points_awarded, NO_POINTS)
        self.assertEqual(Points.objects.count(), 1)


class MatchModelTests(BaseTestCase):
    def test_result_is_set_automatically(self):
        self.finish(2, 1)
        self.assertEqual(self.match.result, Match.Result.HOME)
        self.finish(1, 1)
        self.assertEqual(self.match.result, Match.Result.DRAW)
        self.finish(0, 1)
        self.assertEqual(self.match.result, Match.Result.AWAY)

    def test_future_scheduled_match_is_not_locked(self):
        self.assertFalse(self.match.is_locked)

    def test_match_is_locked_after_start_time(self):
        self.match.scheduled_at = timezone.now() - timedelta(minutes=1)
        self.match.save()
        self.assertTrue(self.match.is_locked)

    def test_match_is_locked_when_not_scheduled(self):
        self.match.status = Match.Status.LIVE
        self.match.save()
        self.assertTrue(self.match.is_locked)


class PredictViewTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username="tester", password="haslo-testowe-123")
        self.url = reverse("typer:predict", args=[self.match.id])

    def test_anonymous_user_is_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_can_submit_prediction(self):
        self.client.post(self.url, {"predicted_home": 2, "predicted_away": 1})
        self.assertEqual(Prediction.objects.filter(user=self.user, match=self.match).count(), 1)

    def test_editing_does_not_create_second_prediction(self):
        self.client.post(self.url, {"predicted_home": 2, "predicted_away": 1})
        self.client.post(self.url, {"predicted_home": 0, "predicted_away": 0})
        predictions = Prediction.objects.filter(user=self.user, match=self.match)
        self.assertEqual(predictions.count(), 1)
        self.assertEqual(predictions.first().predicted_home, 0)

    def test_cannot_predict_after_match_started(self):
        self.match.scheduled_at = timezone.now() - timedelta(minutes=1)
        self.match.save()
        self.client.post(self.url, {"predicted_home": 2, "predicted_away": 1})
        self.assertEqual(Prediction.objects.count(), 0)