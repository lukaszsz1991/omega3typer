import os, tempfile
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase, SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from types import SimpleNamespace
from .constants import POINTS_EXACT_SCORE, POINTS_GOAL_DIFFERENCE, POINTS_WINNER, NO_POINTS, UPCOMING_DAYS
from .models import User, Sport, Team, League, Match, Prediction, Points, TypingGroup, TypingGroupMember, outcome
from .utils import assign_ranks


class OutcomeTests(TestCase):
    def test_outcome(self):
        self.assertEqual(outcome(2, 1), "home")
        self.assertEqual(outcome(0, 3), "away")
        self.assertEqual(outcome(1, 1), "draw")


class BaseTestCase(TestCase):
    """Wspólne dane: użytkownik, sport, drużyny, liga i mecz w przyszłości."""

    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="haslo-testowe-123")
        self.sport = Sport.objects.create(name="Piłka nożna")
        self.home = Team.objects.create(name="Drużyna A", sport=self.sport)
        self.away = Team.objects.create(name="Drużyna B", sport=self.sport)
        self.league = League.objects.create(
            name="Test Liga", sport=self.sport,
            year=date.today().year + 1,
            end_date=date.today() + timedelta(days=365),
        )
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
            ((2, 1), (3, 2), POINTS_GOAL_DIFFERENCE),  # ta sama różnica
            ((2, 1), (1, 0), POINTS_GOAL_DIFFERENCE),
            ((2, 1), (3, 0), POINTS_WINNER),  # dobry zwycięzca, inna różnica
            ((2, 1), (1, 1), NO_POINTS),  # remis zamiast wygranej
            ((2, 1), (0, 1), NO_POINTS),  # zły zwycięzca
            ((1, 1), (1, 1), POINTS_EXACT_SCORE),  # dokładny remis
            ((2, 2), (1, 1), POINTS_GOAL_DIFFERENCE),  # trafiony remis, inny wynik
            ((1, 1), (2, 1), NO_POINTS),  # typ wygranej, był remis
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
        self.assertIn("/login/", response.url)  # noqa

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


class TypingGroupViewTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.other = User.objects.create_user(username="drugi", password="haslo-testowe-123")
        self.client.login(username="tester", password="haslo-testowe-123")
        self.other_client = Client()
        self.other_client.login(username="drugi", password="haslo-testowe-123")

    def create_group(self):
        self.client.post(reverse("typer:group_create"), {"name": "Znajomi", "league": self.league.id})
        return TypingGroup.objects.get(name="Znajomi")

    def test_create_group_sets_owner_member_and_code(self):
        group = self.create_group()
        self.assertEqual(group.owner, self.user)
        self.assertTrue(group.is_private)
        self.assertTrue(group.invite_code)
        self.assertIn(self.user, group.members.all())

    def test_non_member_gets_404(self):
        group = self.create_group()
        response = self.other_client.get(reverse("typer:group_detail", args=[group.id]))
        self.assertEqual(response.status_code, 404)

    def test_join_with_valid_code(self):
        group = self.create_group()
        response = self.other_client.post(reverse("typer:group_join"), {"code": group.invite_code})
        self.assertRedirects(response, reverse("typer:group_detail", args=[group.id]))
        self.assertIn(self.other, group.members.all())

    def test_join_with_invalid_code(self):
        group = self.create_group()
        self.other_client.post(reverse("typer:group_join"), {"code": "zly-kod"})
        self.assertNotIn(self.other, group.members.all())

    def test_joining_twice_does_not_duplicate_membership(self):
        group = self.create_group()
        for _ in range(2):
            self.other_client.post(reverse("typer:group_join"), {"code": group.invite_code})
        self.assertEqual(
            TypingGroupMember.objects.filter(group=group, user=self.other).count(), 1
        )

    def test_anonymous_user_cannot_join(self):
        group = self.create_group()
        self.client.logout()
        response = self.client.post(reverse("typer:group_join"), {"code": group.invite_code})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(group.members.count(), 1)

    def test_cannot_join_group_of_finished_league(self):
        group = self.create_group()
        self.league.end_date = date.today() - timedelta(days=1)
        self.league.save()
        self.other_client.post(reverse("typer:group_join"), {"code": group.invite_code})
        self.assertNotIn(self.other, group.members.all())

    def join(self, group):
        self.other_client.post(reverse("typer:group_join"), {"code": group.invite_code})

    def test_owner_can_remove_member(self):
        group = self.create_group()
        self.join(group)
        self.client.post(reverse("typer:group_remove_member", args=[group.id, self.other.id]))
        self.assertNotIn(self.other, group.members.all())

    def test_non_owner_cannot_remove_member(self):
        group = self.create_group()
        self.join(group)
        response = self.other_client.post(reverse("typer:group_remove_member", args=[group.id, self.user.id]))
        self.assertEqual(response.status_code, 404)
        self.assertIn(self.user, group.members.all())

    def test_owner_cannot_leave_group(self):
        group = self.create_group()
        self.client.post(reverse("typer:group_leave", args=[group.id]))
        self.assertIn(self.user, group.members.all())

    def test_member_can_leave_group(self):
        group = self.create_group()
        self.join(group)
        self.other_client.post(reverse("typer:group_leave", args=[group.id]))
        self.assertNotIn(self.other, group.members.all())

    def test_owner_can_regenerate_code(self):
        group = self.create_group()
        old_code = group.invite_code
        self.client.post(reverse("typer:group_regenerate_code", args=[group.id]))
        group.refresh_from_db()
        self.assertNotEqual(group.invite_code, old_code)

    def test_non_owner_cannot_regenerate_code(self):
        group = self.create_group()
        self.join(group)
        response = self.other_client.post(reverse("typer:group_regenerate_code", args=[group.id]))
        self.assertEqual(response.status_code, 404)


class GroupRankingTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.friend = User.objects.create_user(username="kolega", password="haslo-testowe-123")
        self.outsider = User.objects.create_user(username="obcy", password="haslo-testowe-123")
        self.group = TypingGroup.objects.create(name="Znajomi", is_private=True, owner=self.user, league=self.league)
        TypingGroupMember.objects.create(user=self.user, group=self.group)
        TypingGroupMember.objects.create(user=self.friend, group=self.group)
        self.client.login(username="tester", password="haslo-testowe-123")
        self.url = reverse("typer:group_detail", args=[self.group.id])

    def ranking(self):
        return list(self.client.get(self.url).context["ranking"])

    def test_ranking_orders_members_by_points(self):
        self.predict(2, 1)  # tester: dokładny wynik
        Prediction.objects.create(
            user=self.friend, match=self.match, predicted_home=3, predicted_away=0
        )  # kolega: sam zwycięzca
        self.finish(2, 1)
        users = self.ranking()
        self.assertEqual([u.username for u in users], ["tester", "kolega"])
        self.assertEqual(users[0].total_points, POINTS_EXACT_SCORE)
        self.assertEqual(users[1].total_points, POINTS_WINNER)

    def test_member_without_points_is_listed_with_zero(self):
        users = self.ranking()
        self.assertEqual(len(users), 2)
        self.assertTrue(all(u.total_points == 0 for u in users))

    def test_points_of_non_members_are_not_listed(self):
        Prediction.objects.create(
            user=self.outsider, match=self.match, predicted_home=2, predicted_away=1
        )
        self.finish(2, 1)
        names = [u.username for u in self.ranking()]
        self.assertNotIn("obcy", names)

    def test_points_from_other_leagues_are_not_counted(self):
        other_league = League.objects.create(
            name="Inna liga", sport=self.sport,
            year=date.today().year + 1,
            end_date=date.today() + timedelta(days=300),
        )
        other_match = Match.objects.create(
            league=other_league, home_team=self.home, away_team=self.away,
            scheduled_at=timezone.now() + timedelta(days=1),
        )
        Prediction.objects.create(
            user=self.user, match=other_match, predicted_home=1, predicted_away=0
        )
        other_match.home_score, other_match.away_score = 1, 0
        other_match.status = Match.Status.FINISHED
        other_match.save()

        self.assertTrue(all(u.total_points == 0 for u in self.ranking()))


class GlobalRankingTests(BaseTestCase):
    def test_ties_share_rank(self):
        other = User.objects.create_user(username="drugi", password="haslo-testowe-123")
        self.predict(1, 0)
        Prediction.objects.create(
            user=other, match=self.match, predicted_home=1, predicted_away=0
        )
        self.finish(1, 0)
        response = self.client.get(reverse("typer:ranking"))
        self.assertEqual([u.rank for u in response.context["users"]], [1, 1])

    def test_ranking_page_has_league_tables(self):
        self.predict(2, 1)
        self.finish(2, 1)
        response = self.client.get(reverse("typer:ranking"))
        table = response.context["league_tables"][0]
        self.assertEqual(table["league"], self.league)
        self.assertEqual([r.username for r in table["rows"]], ["tester"])


class LeagueViewTests(BaseTestCase):
    def test_league_list_shows_leagues(self):
        response = self.client.get(reverse("typer:league_list"))
        self.assertContains(response, self.league.name)

    def test_league_detail_shows_upcoming_match(self):
        response = self.client.get(reverse("typer:league_detail", args=[self.league.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["upcoming"]), [self.match])

    def test_league_ranking_lists_users_with_points(self):
        self.predict(2, 1)
        self.finish(2, 1)
        response = self.client.get(reverse("typer:league_detail", args=[self.league.id]))
        ranking = response.context["ranking"]
        self.assertEqual([(u.username, u.total_points) for u in ranking],
                         [("tester", POINTS_EXACT_SCORE)])


class MatchCleanTests(BaseTestCase):
    def test_same_team_on_both_sides_is_invalid(self):
        self.match.away_team = self.match.home_team
        with self.assertRaises(ValidationError):
            self.match.clean()


class MatchDetailViewTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.other = User.objects.create_user(username="drugi", password="haslo-testowe-123")
        Prediction.objects.create(user=self.other, match=self.match, predicted_home=1, predicted_away=0)
        self.client.login(username="tester", password="haslo-testowe-123")
        self.url = reverse("typer:match_detail", args=[self.match.id])

    def test_anonymous_user_can_view_match_detail(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["my_prediction"])

    def test_other_predictions_hidden_before_match_start(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["predictions"])

    def test_other_predictions_visible_after_match_start(self):
        self.match.scheduled_at = timezone.now() - timedelta(minutes=1)
        self.match.save()
        response = self.client.get(self.url)
        self.assertEqual(response.context["predictions"].count(), 1)


class MatchListViewTests(BaseTestCase):
    def test_match_list_renders_with_links_to_details(self):
        self.client.login(username="tester", password="haslo-testowe-123")
        response = self.client.get(reverse("typer:match_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("typer:match_detail", args=[self.match.id]))

    def test_filter_by_sport_hides_other_sport(self):
        other_sport = Sport.objects.create(name="Piłka ręczna")
        response = self.client.get(reverse("typer:match_list"), {"sport": other_sport.id})
        self.assertNotContains(response, self.home.name)

    def test_garbage_filter_values_do_not_break_page(self):
        response = self.client.get(reverse("typer:match_list"), {"sport": "abc", "league": "x"})
        self.assertEqual(response.status_code, 200)


class ImportMatchesTests(BaseTestCase):
    def test_import_creates_match_and_is_idempotent(self):
        with tempfile.NamedTemporaryFile(
                "w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        ) as f:
            f.write("league,year,home_team,away_team,scheduled_at,home_score,away_score\n")
            f.write(f"{self.league.name},{self.league.year},Nowa A,Nowa B,2030-01-01 18:00,2,1\n")
        self.addCleanup(os.unlink, f.name)

        call_command("import_matches", f.name)
        call_command("import_matches", f.name)  # drugi raz nie dubluje

        matches = Match.objects.filter(home_team__name="Nowa A")
        self.assertEqual(matches.count(), 1)
        self.assertEqual(matches.first().result, Match.Result.HOME)


class PublicPagesTests(BaseTestCase):
    def test_anonymous_can_view_match_list_and_ranking(self):
        for name in ("typer:match_list", "typer:ranking"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)


class MatchListSectionsTests(BaseTestCase):
    def test_match_from_users_group_league_goes_to_my_section(self):
        group = TypingGroup.objects.create(
            name="Znajomi", is_private=True, owner=self.user, league=self.league
        )
        TypingGroupMember.objects.create(user=self.user, group=group)
        self.client.login(username="tester", password="haslo-testowe-123")
        response = self.client.get(reverse("typer:match_list"))
        self.assertEqual(list(response.context["my_upcoming"]), [self.match])
        self.assertEqual(list(response.context["other_upcoming"]), [])

    def test_anonymous_sees_matches_in_other_section(self):
        response = self.client.get(reverse("typer:match_list"))
        self.assertEqual(list(response.context["my_upcoming"]), [])
        self.assertEqual(list(response.context["other_upcoming"]), [self.match])

    def test_matches_beyond_horizon_are_hidden(self):
        self.match.scheduled_at = timezone.now() + timedelta(days=UPCOMING_DAYS + 5)
        self.match.save()
        response = self.client.get(reverse("typer:match_list"))
        self.assertEqual(list(response.context["other_upcoming"]), [])


class AssignRanksTests(SimpleTestCase):
    def test_ties_share_rank_and_next_is_skipped(self):
        items = [SimpleNamespace(total_points=p) for p in (10, 7, 7, 3)]
        assign_ranks(items)
        self.assertEqual([i.rank for i in items], [1, 2, 2, 4])
