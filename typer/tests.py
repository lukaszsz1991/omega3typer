import os, tempfile
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
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


class BulkPredictTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username="tester", password="haslo-testowe-123")
        self.url = reverse("typer:predict_bulk")
        self.match2 = Match.objects.create(
            league=self.league, home_team=self.away, away_team=self.home,
            scheduled_at=timezone.now() + timedelta(days=2),
        )

    def post(self, data):
        return self.client.post(self.url, data)

    def test_anonymous_user_is_redirected_to_login(self):
        self.client.logout()
        response = self.post({f"home_{self.match.id}": 1, f"away_{self.match.id}": 0})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)  # noqa
        self.assertEqual(Prediction.objects.count(), 0)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_saves_many_predictions_at_once(self):
        self.post({
            f"home_{self.match.id}": 2, f"away_{self.match.id}": 1,
            f"home_{self.match2.id}": 0, f"away_{self.match2.id}": 0,
        })
        self.assertEqual(Prediction.objects.filter(user=self.user).count(), 2)

    def test_editing_does_not_create_second_prediction(self):
        data = {f"home_{self.match.id}": 2, f"away_{self.match.id}": 1}
        self.post(data)
        self.post({f"home_{self.match.id}": 0, f"away_{self.match.id}": 0})
        predictions = Prediction.objects.filter(user=self.user, match=self.match)
        self.assertEqual(predictions.count(), 1)
        self.assertEqual(predictions.first().predicted_home, 0)

    def test_empty_pairs_are_skipped_and_do_not_delete(self):
        self.predict(2, 1)
        self.post({
            f"home_{self.match.id}": "", f"away_{self.match.id}": "",
            f"home_{self.match2.id}": "", f"away_{self.match2.id}": "",
        })
        self.assertEqual(Prediction.objects.count(), 1)
        self.assertEqual(Prediction.objects.get().predicted_home, 2)

    def test_invalid_row_does_not_block_valid_ones(self):
        self.post({
            f"home_{self.match.id}": 2, f"away_{self.match.id}": 1,
            f"home_{self.match2.id}": 100, f"away_{self.match2.id}": 0,
        })
        self.assertEqual(list(Prediction.objects.values_list("match_id", flat=True)), [self.match.id])

    def test_invalid_scores_are_rejected(self):
        for home, away in [(-1, 0), (0, -3), (100, 0), ("abc", 1), (1, ""), ("", 2)]:
            with self.subTest(home=home, away=away):
                self.post({f"home_{self.match.id}": home, f"away_{self.match.id}": away})
                self.assertEqual(Prediction.objects.count(), 0)

    def test_boundary_scores_are_accepted(self):
        self.post({f"home_{self.match.id}": 0, f"away_{self.match.id}": 99})
        self.assertEqual(Prediction.objects.count(), 1)

    def test_cannot_predict_after_match_started(self):
        self.match.scheduled_at = timezone.now() - timedelta(minutes=1)
        self.match.save()
        self.post({f"home_{self.match.id}": 2, f"away_{self.match.id}": 1})
        self.assertEqual(Prediction.objects.count(), 0)

    def test_unknown_match_and_garbage_keys_are_ignored(self):
        response = self.post({"home_999999": 1, "away_999999": 1, "home_x": 1, "home_" + "9" * 30: 1})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Prediction.objects.count(), 0)

    def test_redirects_back_to_safe_next_only(self):
        data = {f"home_{self.match.id}": 1, f"away_{self.match.id}": 0}
        self.assertEqual(self.post({**data, "next": "/leagues/"}).url, "/leagues/")
        self.assertEqual(self.post({**data, "next": "https://evil.example/"}).url, reverse("typer:match_list"))


class SavedPredictionVisibilityTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username="tester", password="haslo-testowe-123")
        TypingGroup.objects.create(name="G", league=self.league, owner=self.user, is_private=True)
        self.group = TypingGroup.objects.get(name="G")
        TypingGroupMember.objects.create(user=self.user, group=self.group)

    def pages(self):
        return [
            reverse("typer:match_list"),
            reverse("typer:league_detail", args=[self.league.id]),
            reverse("typer:group_detail", args=[self.group.id]),
            reverse("typer:match_detail", args=[self.match.id]),
        ]

    def test_unsaved_match_has_inputs_and_no_change_button(self):
        for url in self.pages():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, f'name="home_{self.match.id}"')
                self.assertContains(response, "Zapisz typy")
                self.assertNotContains(response, 'o3-edit">')

    def test_saved_prediction_is_shown_with_change_button(self):
        self.predict(3, 2)
        for url in self.pages():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "<strong>3:2</strong>", html=True)
                self.assertContains(response, 'o3-edit">Zmień typ</button>')

    def test_anonymous_sees_no_inputs(self):
        self.client.logout()
        for url in (self.pages()[0], self.pages()[1], self.pages()[3]):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertNotContains(response, f'name="home_{self.match.id}"')
                self.assertNotContains(response, "Zapisz typy")

    def test_group_lists_only_matches_of_its_league(self):
        other_league = League.objects.create(
            name="Inna", sport=self.sport, year=date.today().year + 1,
            end_date=date.today() + timedelta(days=300))
        other = Match.objects.create(league=other_league, home_team=self.home, away_team=self.away,
                                     scheduled_at=timezone.now() + timedelta(days=1))
        response = self.client.get(reverse("typer:group_detail", args=[self.group.id]))
        self.assertContains(response, f'name="home_{self.match.id}"')
        self.assertNotContains(response, f'name="home_{other.id}"')

    def test_match_list_does_not_query_per_match(self):
        for i in range(5):
            Match.objects.create(league=self.league, home_team=self.home, away_team=self.away,
                                 scheduled_at=timezone.now() + timedelta(days=1, hours=i))
        with self.assertNumQueries(8):
            self.client.get(reverse("typer:match_list"))


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

    def test_cannot_create_group_for_finished_league(self):
        self.league.end_date = date.today() - timedelta(days=1)
        self.league.save()
        self.client.post(reverse("typer:group_create"), {"name": "Stara", "league": self.league.id})
        self.assertFalse(TypingGroup.objects.filter(name="Stara").exists())

    def test_join_with_empty_code_does_not_crash(self):
        response = self.other_client.post(reverse("typer:group_join"), {"code": ""})
        self.assertEqual(response.status_code, 200)


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

    def test_ranking_is_empty_without_points(self):
        response = self.client.get(reverse("typer:ranking"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["users"], [])
        self.assertEqual(response.context["league_tables"], [])


class LeagueViewTests(BaseTestCase):
    def test_league_list_shows_leagues(self):
        response = self.client.get(reverse("typer:league_list"))
        self.assertContains(response, self.league.name)

    def test_league_detail_shows_upcoming_match(self):
        response = self.client.get(reverse("typer:league_detail", args=[self.league.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["matches"]), [self.match])

    def test_league_ranking_lists_users_with_points(self):
        self.predict(2, 1)
        self.finish(2, 1)
        response = self.client.get(reverse("typer:league_detail", args=[self.league.id]))
        ranking = response.context["ranking"]
        self.assertEqual([(u.username, u.total_points) for u in ranking],
                         [("tester", POINTS_EXACT_SCORE)])


class LeagueRoundsTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        now = timezone.now()
        self.r1 = self.make_match(1, now - timedelta(days=7), finished=(2, 1))
        self.r2 = self.make_match(2, now + timedelta(days=2))
        self.r3 = self.make_match(3, now + timedelta(days=9))
        self.url = reverse("typer:league_detail", args=[self.league.id])

    def make_match(self, round_number, when, finished=None):
        match = Match.objects.create(league=self.league, home_team=self.home, away_team=self.away,
                                     scheduled_at=when, round=round_number)
        if finished:
            match.home_score, match.away_score = finished
            match.status = Match.Status.FINISHED
            match.save()
        return match

    def get(self, **params):
        return self.client.get(self.url, params).context

    def test_defaults_to_first_round_with_unplayed_matches(self):
        context = self.get()
        self.assertEqual(context["selected_round"], 2)
        self.assertEqual(list(context["matches"]), [self.r2])
        self.assertEqual(context["round_numbers"], [1, 2, 3])
        self.assertEqual((context["prev_round"], context["next_round"]), (1, 3))

    def test_selects_requested_round_including_finished(self):
        context = self.get(round=1)
        self.assertEqual(list(context["matches"]), [self.r1])
        self.assertIsNone(context["prev_round"])
        self.assertTrue(context["no_open_matches"])

    def test_garbage_round_falls_back_to_default(self):
        for value in ("abc", "99", "-1"):
            with self.subTest(value=value):
                self.assertEqual(self.get(round=value)["selected_round"], 2)

    def test_defaults_to_last_round_when_all_finished(self):
        for match in (self.r2, self.r3):
            match.home_score, match.away_score, match.status = 0, 0, Match.Status.FINISHED
            match.save()
        self.assertEqual(self.get()["selected_round"], 3)

    def test_matches_without_round_are_in_separate_group(self):
        # mecz z BaseTestCase nie ma kolejki
        context = self.get(round="none")
        self.assertTrue(context["has_unassigned"])
        self.assertTrue(context["unassigned"])
        self.assertIsNone(context["selected_round"])
        self.assertEqual(list(context["matches"]), [self.match])

    def test_none_falls_back_when_no_match_is_unassigned(self):
        self.match.round = 1
        self.match.save()
        context = self.get(round="none")
        self.assertFalse(context["has_unassigned"])
        self.assertFalse(context["unassigned"])
        self.assertEqual(context["selected_round"], 1)  # kolejka 1 ma teraz niezagrany mecz

    def test_league_without_rounds_shows_all_matches_in_one_list(self):
        Match.objects.filter(round__isnull=False).delete()
        context = self.get()
        self.assertEqual(context["round_numbers"], [])
        self.assertEqual(list(context["matches"]), [self.match])

    def test_finished_match_shows_score_my_prediction_and_points(self):
        Prediction.objects.create(user=self.user, match=self.r1, predicted_home=2, predicted_away=1)
        self.r1.save()  # przelicza punkty
        self.client.login(username="tester", password="haslo-testowe-123")
        response = self.client.get(self.url, {"round": 1})
        self.assertContains(response, "2:1")
        self.assertContains(response, f"{POINTS_EXACT_SCORE} pkt")
        self.assertNotContains(response, "Zapisz typy")  # w kolejce nie ma już czego typować

    def test_round_is_kept_after_saving_predictions(self):
        self.client.login(username="tester", password="haslo-testowe-123")
        response = self.client.get(self.url, {"round": 3})
        self.assertContains(response, f'name="next" value="{self.url}?round=3"')


class MatchCleanTests(BaseTestCase):
    def test_same_team_on_both_sides_is_invalid(self):
        self.match.away_team = self.match.home_team
        with self.assertRaises(ValidationError):
            self.match.clean()

    def test_team_from_other_sport_is_invalid(self):
        other_sport = Sport.objects.create(name="Piłka ręczna")
        foreign_team = Team.objects.create(name="Obca", sport=other_sport)
        self.match.away_team = foreign_team
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

    def test_anonymous_does_not_see_predict_button(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertNotContains(response, "Zapisz typy")


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


class LeagueModelTests(BaseTestCase):
    def test_str(self):
        self.assertEqual(str(self.league), f"Test Liga {self.league.year}")

    def test_league_is_not_finished_on_its_last_day(self):
        self.league.end_date = date.today()
        self.assertFalse(self.league.is_finished)

    def test_league_is_finished_after_end_date(self):
        self.league.end_date = date.today() - timedelta(days=1)
        self.assertTrue(self.league.is_finished)

    def test_name_and_year_must_be_unique(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            League.objects.create(
                name=self.league.name, sport=self.sport,
                year=self.league.year, end_date=date.today() + timedelta(days=10),
            )


class TeamModelTests(BaseTestCase):
    def test_team_name_must_be_unique_within_sport(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Team.objects.create(name=self.home.name, sport=self.sport)

    def test_same_name_is_allowed_in_another_sport(self):
        other_sport = Sport.objects.create(name="Piłka ręczna")
        team = Team.objects.create(name=self.home.name, sport=other_sport)
        self.assertEqual(team.name, self.home.name)


class TypingGroupModelTests(BaseTestCase):
    def make_group(self, **kwargs):
        return TypingGroup.objects.create(
            name="Znajomi", league=self.league, owner=self.user, **kwargs
        )

    def test_private_group_gets_invite_code(self):
        group = self.make_group(is_private=True)
        self.assertTrue(group.invite_code)
        self.assertLessEqual(len(group.invite_code), 20)

    def test_public_group_has_no_invite_code(self):
        group = self.make_group(is_private=False)
        self.assertFalse(group.invite_code)

    def test_group_is_active_while_league_is_running(self):
        self.assertTrue(self.make_group().is_active)

    def test_group_is_inactive_after_league_end(self):
        group = self.make_group()
        self.league.end_date = date.today() - timedelta(days=1)
        self.league.save()
        group.refresh_from_db()
        self.assertFalse(group.is_active)

    def test_regenerate_invite_code_changes_code(self):
        group = self.make_group(is_private=True)
        old_code = group.invite_code
        group.regenerate_invite_code()
        group.refresh_from_db()
        self.assertNotEqual(group.invite_code, old_code)

    def test_user_cannot_be_member_twice(self):
        group = self.make_group(is_private=True)
        TypingGroupMember.objects.create(user=self.user, group=group)
        with self.assertRaises(IntegrityError), transaction.atomic():
            TypingGroupMember.objects.create(user=self.user, group=group)


class PredictionModelTests(BaseTestCase):
    def test_user_can_predict_match_only_once(self):
        self.predict(1, 0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.predict(2, 2)


class MatchStrTests(BaseTestCase):
    def test_str_of_scheduled_match(self):
        self.assertIn("Drużyna A - Drużyna B", str(self.match))

    def test_str_of_finished_match_shows_score(self):
        self.finish(2, 1)
        self.assertEqual(str(self.match), "Drużyna A 2:1 Drużyna B")


class LoginRequiredTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.group = TypingGroup.objects.create(
            name="Znajomi", league=self.league, owner=self.user, is_private=True
        )
        TypingGroupMember.objects.create(user=self.user, group=self.group)

    def assert_redirects_to_login(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("typer:login")))

    def test_anonymous_is_redirected_from_protected_pages(self):
        urls = [
            reverse("typer:group_list"),
            reverse("typer:group_create"),
            reverse("typer:group_join"),
            reverse("typer:group_detail", args=[self.group.id]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assert_redirects_to_login(self.client.get(url))

    def test_anonymous_cannot_use_group_actions(self):
        urls = [
            reverse("typer:group_leave", args=[self.group.id]),
            reverse("typer:group_regenerate_code", args=[self.group.id]),
            reverse("typer:group_remove_member", args=[self.group.id, self.user.id]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assert_redirects_to_login(self.client.post(url))
        self.assertEqual(self.group.members.count(), 1)

    def test_group_actions_reject_get_requests(self):
        self.client.login(username="tester", password="haslo-testowe-123")
        for name in ("typer:group_leave", "typer:group_regenerate_code"):
            with self.subTest(name=name):
                response = self.client.get(reverse(name, args=[self.group.id]))
                self.assertEqual(response.status_code, 405)


class GroupListViewTests(BaseTestCase):
    def test_group_list_splits_active_and_archived(self):
        old_league = League.objects.create(
            name="Stara liga", sport=self.sport, year=2020,
            end_date=date.today() - timedelta(days=10),
        )
        active = TypingGroup.objects.create(name="Aktualna", league=self.league, owner=self.user)
        archived = TypingGroup.objects.create(name="Dawna", league=old_league, owner=self.user)
        for group in (active, archived):
            TypingGroupMember.objects.create(user=self.user, group=group)

        self.client.login(username="tester", password="haslo-testowe-123")
        response = self.client.get(reverse("typer:group_list"))
        self.assertEqual(response.context["active"], [active])
        self.assertEqual(response.context["archived"], [archived])

    def test_archived_group_detail_redirects_to_list(self):
        group = TypingGroup.objects.create(name="Dawna", league=self.league, owner=self.user)
        TypingGroupMember.objects.create(user=self.user, group=group)
        self.league.end_date = date.today() - timedelta(days=1)
        self.league.save()

        self.client.login(username="tester", password="haslo-testowe-123")
        response = self.client.get(reverse("typer:group_detail", args=[group.id]))
        self.assertRedirects(response, reverse("typer:group_list"))


class RegistrationTests(TestCase):
    def setUp(self):
        self.url = reverse("typer:register")
        self.data = {
            "username": "nowy",
            "email": "nowy@example.com",
            "password1": "Sup3r-tajne-haslo-2026",
            "password2": "Sup3r-tajne-haslo-2026",
        }

    def test_valid_registration_creates_user_and_redirects(self):
        response = self.client.post(self.url, self.data)
        self.assertRedirects(response, reverse("typer:home"))
        self.assertTrue(User.objects.filter(username="nowy").exists())

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(username="stary", email="Nowy@Example.com", password="haslo-testowe-123")
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="nowy").exists())

    def test_password_mismatch_is_rejected(self):
        self.data["password2"] = "inne-haslo-2026"
        self.client.post(self.url, self.data)
        self.assertFalse(User.objects.filter(username="nowy").exists())

    def test_email_is_required(self):
        self.data["email"] = ""
        self.client.post(self.url, self.data)
        self.assertFalse(User.objects.filter(username="nowy").exists())


class MatchAdminTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        User.objects.create_superuser(username="admin", password="haslo-admina-123")
        self.client.login(username="admin", password="haslo-admina-123")
        self.url = reverse("admin:typer_match_changelist")
        self.other_league = League.objects.create(
            name="Inna liga", sport=self.sport, year=date.today().year + 1,
            end_date=date.today() + timedelta(days=300))
        self.third = Team.objects.create(name="Wisła", sport=self.sport)
        self.m1 = self.add(self.league, 1, self.home, self.away)
        self.m2 = self.add(self.league, 2, self.home, self.third)
        self.m3 = self.add(self.other_league, 7, self.third, self.away)

    def add(self, league, round_number, home, away):
        return Match.objects.create(league=league, round=round_number, home_team=home, away_team=away,
                                    scheduled_at=timezone.now() + timedelta(days=3))

    def found(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200)
        return set(response.context["cl"].queryset) - {self.match}

    def test_changelist_loads_and_shows_score(self):
        self.finish(2, 1)
        self.assertContains(self.client.get(self.url), "2:1")

    def test_filter_by_league(self):
        self.assertEqual(self.found(league__id__exact=self.other_league.id), {self.m3})

    def test_filter_by_round(self):
        self.assertEqual(self.found(round=2), {self.m2})

    def test_filter_by_league_and_round(self):
        self.assertEqual(self.found(league__id__exact=self.league.id, round=7), set())
        self.assertEqual(self.found(league__id__exact=self.other_league.id, round=7), {self.m3})

    def test_round_filter_offers_only_rounds_of_selected_league(self):
        response = self.client.get(self.url, {"league__id__exact": self.league.id})
        self.assertContains(response, "Kolejka 1")
        self.assertContains(response, "Kolejka 2")
        self.assertNotContains(response, "Kolejka 7")

    def test_garbage_round_is_ignored(self):
        self.assertEqual(self.found(round="abc"), {self.m1, self.m2, self.m3})

    def test_search_by_team_name(self):
        self.assertEqual(self.found(q="Wisła"), {self.m2, self.m3})

    def test_add_form_loads(self):
        self.assertEqual(self.client.get(reverse("admin:typer_match_add")).status_code, 200)


class HomePageTests(BaseTestCase):
    def test_anonymous_sees_hero_next_matches_and_scoring(self):
        response = self.client.get(reverse("typer:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Załóż konto")
        self.assertContains(response, self.home.name)
        self.assertNotContains(response, f'name="home_{self.match.id}"')
        self.assertEqual(response.context["points"]["exact"], POINTS_EXACT_SCORE)

    def test_logged_in_sees_matches_to_predict(self):
        self.client.login(username="tester", password="haslo-testowe-123")
        response = self.client.get(reverse("typer:home"))
        self.assertContains(response, f'name="home_{self.match.id}"')
        self.assertEqual(list(response.context["todo"]), [self.match])
        self.assertEqual(response.context["my_points"], 0)
        self.assertIsNone(response.context["my_rank"])

    def test_predicted_match_leaves_the_todo_list(self):
        self.predict(1, 0)
        self.client.login(username="tester", password="haslo-testowe-123")
        response = self.client.get(reverse("typer:home"))
        self.assertEqual(list(response.context["todo"]), [])
        self.assertEqual(response.context["predictions_count"], 1)

    def test_stats_show_points_and_rank(self):
        self.predict(2, 1)
        self.finish(2, 1)
        self.client.login(username="tester", password="haslo-testowe-123")
        context = self.client.get(reverse("typer:home")).context
        self.assertEqual((context["my_points"], context["my_rank"]), (POINTS_EXACT_SCORE, 1))

    def test_todo_prefers_leagues_from_users_groups(self):
        other_league = League.objects.create(
            name="Inna", sport=self.sport, year=date.today().year + 1,
            end_date=date.today() + timedelta(days=300))
        other = Match.objects.create(league=other_league, home_team=self.home, away_team=self.away,
                                     scheduled_at=timezone.now() + timedelta(hours=3))
        group = TypingGroup.objects.create(name="G", league=self.league, owner=self.user, is_private=True)
        TypingGroupMember.objects.create(user=self.user, group=group)
        self.client.login(username="tester", password="haslo-testowe-123")
        todo = list(self.client.get(reverse("typer:home")).context["todo"])
        self.assertEqual(todo, [self.match])
        self.assertNotIn(other, todo)


class AuthPagesTests(TestCase):
    def test_auth_pages_render_with_styled_forms(self):
        for name in ("typer:login", "typer:register", "typer:password_reset"):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "auth-form")


class MatchListSingleFormTests(BaseTestCase):
    def test_both_upcoming_sections_share_one_form_and_one_save_button(self):
        group = TypingGroup.objects.create(name="G", league=self.league, owner=self.user, is_private=True)
        TypingGroupMember.objects.create(user=self.user, group=group)
        other_league = League.objects.create(
            name="Inna", sport=self.sport, year=date.today().year + 1,
            end_date=date.today() + timedelta(days=300))
        other = Match.objects.create(league=other_league, home_team=self.home, away_team=self.away,
                                     scheduled_at=timezone.now() + timedelta(days=1))
        self.client.login(username="tester", password="haslo-testowe-123")
        response = self.client.get(reverse("typer:match_list"))
        self.assertContains(response, f'name="home_{self.match.id}"')
        self.assertContains(response, f'name="home_{other.id}"')
        self.assertContains(response, 'class="btn btn-primary o3-save"', count=1)
        self.assertContains(response, 'action="/predictions/save/"', count=1)

    def test_no_save_button_without_open_matches(self):
        self.match.status = Match.Status.FINISHED
        self.match.home_score, self.match.away_score = 1, 0
        self.match.save()
        self.client.login(username="tester", password="haslo-testowe-123")
        self.assertNotContains(self.client.get(reverse("typer:match_list")), 'class="btn btn-primary o3-save"')
